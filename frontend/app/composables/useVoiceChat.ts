import type {
  VoiceState,
  ConnectionState,
  ServerMessage,
  ServerDebugMessage,
} from '~/types/voice'

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  ts: number // Date.now()
  audioUrl?: string // Object URL for playback
}

export interface VoiceChatOptions {
  onDebugEvent?: (msg: ServerDebugMessage) => void
}

/**
 * Composable for voice chat over WebSocket.
 *
 * Handles:
 * - WebSocket connection lifecycle
 * - Mic capture → PCM 16-bit 16kHz mono via AudioWorklet
 * - Sending audio binary frames to backend
 * - Receiving JSON events + WAV binary audio from backend
 * - Playback of received WAV audio via AudioContext
 */
export function useVoiceChat(options: VoiceChatOptions = {}) {
  const config = useRuntimeConfig()

  // ── Reactive state ──────────────────────────────────────────────
  const voiceState = ref<VoiceState>('idle')
  const connectionState = ref<ConnectionState>('disconnected')
  const partialTranscription = ref('')
  const finalTranscription = ref('')
  const llmResponse = ref('')
  const errorMessage = ref<string | null>(null)
  const threadId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])

  // ── Internals (not reactive) ────────────────────────────────────
  let ws: WebSocket | null = null
  let audioContext: AudioContext | null = null
  let mediaStream: MediaStream | null = null
  let workletNode: AudioWorkletNode | null = null
  let sourceNode: MediaStreamAudioSourceNode | null = null
  let _userPcmChunks: Int16Array[] = []

  // ── WebSocket connection ────────────────────────────────────────
  function connect(existingThreadId?: string | null) {
    if (ws && ws.readyState <= WebSocket.OPEN) return

    const wsBase = config.public.apiBase.replace('http://', 'ws://').replace('https://', 'wss://')
    let url = `${wsBase}/ws/voice-chat`
    if (existingThreadId) {
      url += `?thread_id=${encodeURIComponent(existingThreadId)}`
    }

    connectionState.value = 'connecting'
    ws = new WebSocket(url)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      connectionState.value = 'connected'
      errorMessage.value = null
    }

    ws.onclose = () => {
      connectionState.value = 'disconnected'
      voiceState.value = 'idle'
      _stopMic()
    }

    ws.onerror = () => {
      connectionState.value = 'error'
      errorMessage.value = 'WebSocket connection failed'
    }

    ws.onmessage = (event: MessageEvent) => {
      if (event.data instanceof ArrayBuffer) {
        // Store audio blob URL on the most recent assistant message
        const blob = new Blob([event.data.slice(0)], { type: 'audio/wav' })
        const url = URL.createObjectURL(blob)
        const lastAssistant = [...messages.value].reverse().find(m => m.role === 'assistant')
        if (lastAssistant) {
          lastAssistant.audioUrl = url
        }
        _playAudio(event.data)
        return
      }

      // Text frame = JSON message
      try {
        const msg: ServerMessage = JSON.parse(event.data)
        _handleMessage(msg)
      } catch (e) {
        console.error('Failed to parse WS message:', e)
      }
    }
  }

  function disconnect() {
    _stopMic()
    // Revoke all audio object URLs
    for (const msg of messages.value) {
      if (msg.audioUrl) URL.revokeObjectURL(msg.audioUrl)
    }
    if (ws) {
      ws.close()
      ws = null
    }
    connectionState.value = 'disconnected'
    voiceState.value = 'idle'
    threadId.value = null
    messages.value = []
    _userPcmChunks = []
  }

  // ── Message handling ────────────────────────────────────────────
  function _handleMessage(msg: ServerMessage) {
    switch (msg.type) {
      case 'state':
        voiceState.value = msg.state
        // Capture thread_id from initial state message
        if (msg.thread_id) {
          threadId.value = msg.thread_id
        }
        break

      case 'stt_partial':
        partialTranscription.value = msg.text
        break

      case 'stt_final': {
        finalTranscription.value = msg.text
        partialTranscription.value = ''
        // Create audio blob from accumulated user PCM chunks
        let audioUrl: string | undefined
        if (_userPcmChunks.length > 0) {
          const totalLength = _userPcmChunks.reduce((sum, c) => sum + c.length, 0)
          const merged = new Int16Array(totalLength)
          let offset = 0
          for (const chunk of _userPcmChunks) {
            merged.set(chunk, offset)
            offset += chunk.length
          }
          audioUrl = URL.createObjectURL(_createWavBlob(merged, 16000))
          _userPcmChunks = []
        }
        // Add user message to history
        messages.value.push({
          role: 'user',
          text: msg.text,
          ts: Date.now(),
          audioUrl,
        })
        break
      }

      case 'llm_complete':
        llmResponse.value = msg.text
        // Add assistant message to history
        messages.value.push({
          role: 'assistant',
          text: msg.text,
          ts: Date.now(),
        })
        break

      case 'turn_complete':
        // Turn is done — state will be set to idle by the state message
        break

      case 'error':
        errorMessage.value = msg.message
        break

      case 'debug':
        options.onDebugEvent?.(msg)
        break
    }
  }

  // ── WAV encoding helper ────────────────────────────────────────
  function _createWavBlob(pcmData: Int16Array, sampleRate: number): Blob {
    const header = new ArrayBuffer(44)
    const v = new DataView(header)
    const dataSize = pcmData.byteLength
    v.setUint32(0, 0x52494646, false)  // RIFF
    v.setUint32(4, 36 + dataSize, true)
    v.setUint32(8, 0x57415645, false)  // WAVE
    v.setUint32(12, 0x666d7420, false) // fmt
    v.setUint32(16, 16, true)
    v.setUint16(20, 1, true)           // PCM
    v.setUint16(22, 1, true)           // mono
    v.setUint32(24, sampleRate, true)
    v.setUint32(28, sampleRate * 2, true) // byteRate
    v.setUint16(32, 2, true)           // blockAlign
    v.setUint16(34, 16, true)          // bitsPerSample
    v.setUint32(36, 0x64617461, false) // data
    v.setUint32(40, dataSize, true)
    return new Blob([header, pcmData.buffer], { type: 'audio/wav' })
  }

  // ── Mic capture ─────────────────────────────────────────────────

  /**
   * AudioWorklet processor code (inline string).
   * Captures Float32 samples, downsamples to 16kHz, converts to Int16 PCM,
   * and posts the binary buffer to the main thread.
   */
  const WORKLET_CODE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._buffer = []
    this._targetRate = 16000
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input[0]) return true

    const samples = input[0] // Float32Array, mono channel 0
    // Accumulate samples — we'll downsample in chunks
    for (let i = 0; i < samples.length; i++) {
      this._buffer.push(samples[i])
    }

    // Send ~4096 samples at target rate (~256ms of audio)
    // sampleRate is the AudioContext sample rate (usually 48000)
    const ratio = sampleRate / this._targetRate
    const targetChunkSize = 4096
    const neededSamples = Math.ceil(targetChunkSize * ratio)

    if (this._buffer.length >= neededSamples) {
      // Downsample
      const downsampled = new Int16Array(targetChunkSize)
      for (let i = 0; i < targetChunkSize; i++) {
        const srcIndex = Math.round(i * ratio)
        const sample = this._buffer[Math.min(srcIndex, this._buffer.length - 1)]
        // Clamp and convert Float32 [-1,1] to Int16
        downsampled[i] = Math.max(-32768, Math.min(32767, Math.round(sample * 32767)))
      }
      this._buffer = this._buffer.slice(neededSamples)

      this.port.postMessage(downsampled.buffer, [downsampled.buffer])
    }

    return true
  }
}

registerProcessor('pcm-capture-processor', PcmCaptureProcessor)
`

  async function _startMic() {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: { ideal: 48000 },
          echoCancellation: true,
          noiseSuppression: true,
        },
      })

      audioContext = new AudioContext({ sampleRate: 48000 })

      // Load worklet from inline code via Blob URL
      const blob = new Blob([WORKLET_CODE], { type: 'application/javascript' })
      const workletUrl = URL.createObjectURL(blob)
      await audioContext.audioWorklet.addModule(workletUrl)
      URL.revokeObjectURL(workletUrl)

      sourceNode = audioContext.createMediaStreamSource(mediaStream)
      workletNode = new AudioWorkletNode(audioContext, 'pcm-capture-processor')

      workletNode.port.onmessage = (e: MessageEvent) => {
        const pcmBuffer = e.data as ArrayBuffer
        // Accumulate a copy for user audio playback
        _userPcmChunks.push(new Int16Array(pcmBuffer.slice(0)))
        if (ws && ws.readyState === WebSocket.OPEN && voiceState.value === 'listening') {
          ws.send(pcmBuffer)
        }
      }

      sourceNode.connect(workletNode)
      // Do NOT connect workletNode to destination — that would play back mic audio.
      // The AudioWorkletNode stays alive as long as it has an input connection.
    } catch (err) {
      console.error('Mic capture failed:', err)
      errorMessage.value = 'Microphone access denied or unavailable'
      throw err
    }
  }

  function _stopMic() {
    if (workletNode) {
      workletNode.disconnect()
      workletNode = null
    }
    if (sourceNode) {
      sourceNode.disconnect()
      sourceNode = null
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop())
      mediaStream = null
    }
    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close()
      audioContext = null
    }
  }

  // ── Audio playback ──────────────────────────────────────────────
  async function _playAudio(wavBuffer: ArrayBuffer) {
    try {
      // Create a fresh context for playback (mic context may be closed)
      const playCtx = new AudioContext()
      const audioBuffer = await playCtx.decodeAudioData(wavBuffer.slice(0))
      const source = playCtx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(playCtx.destination)
      source.onended = () => {
        playCtx.close()
      }
      source.start()
    } catch (err) {
      console.error('Audio playback failed:', err)
    }
  }

  // ── Public actions ──────────────────────────────────────────────

  async function startListening() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      errorMessage.value = 'Not connected'
      return
    }
    if (voiceState.value !== 'idle') return

    errorMessage.value = null
    partialTranscription.value = ''
    finalTranscription.value = ''
    llmResponse.value = ''
    _userPcmChunks = []

    try {
      await _startMic()
      ws.send(JSON.stringify({ type: 'start_listening' }))
    } catch {
      // errorMessage already set in _startMic
    }
  }

  function stopListening() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    if (voiceState.value !== 'listening') return

    _stopMic()
    ws.send(JSON.stringify({ type: 'stop_listening' }))
  }

  function cancel() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    _stopMic()
    ws.send(JSON.stringify({ type: 'cancel' }))
  }

  function setVoice(voice: string | null) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({ type: 'set_voice', voice }))
  }

  /**
   * Load conversation history from an existing thread into messages.
   * Call this after connecting to a thread that has prior turns.
   */
  async function loadThreadHistory(id: string) {
    try {
      const config = useRuntimeConfig()
      const data = await $fetch<{ turns: Array<{ role: string; text: string; created_at: string }> }>(
        `${config.public.apiBase}/api/voice/threads/${id}`
      )
      if (data.turns) {
        messages.value = data.turns.map(t => ({
          role: t.role as 'user' | 'assistant',
          text: t.text,
          ts: new Date(t.created_at).getTime(),
        }))
      }
    } catch (err) {
      console.error('Failed to load thread history:', err)
    }
  }

  // ── Cleanup on unmount ──────────────────────────────────────────
  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    voiceState: readonly(voiceState),
    connectionState: readonly(connectionState),
    partialTranscription: readonly(partialTranscription),
    finalTranscription: readonly(finalTranscription),
    llmResponse: readonly(llmResponse),
    errorMessage: readonly(errorMessage),
    threadId: readonly(threadId),
    messages: readonly(messages),

    // Actions
    connect,
    disconnect,
    startListening,
    stopListening,
    cancel,
    setVoice,
    loadThreadHistory,
  }
}
