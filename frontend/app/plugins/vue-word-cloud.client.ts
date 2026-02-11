import VueWordCloud from 'vuewordcloud'

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.component('VueWordCloud', VueWordCloud)
})
