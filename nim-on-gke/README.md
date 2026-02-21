# NVIDIA NIM on GKE with Pulumi (TypeScript)

This directory contains a simple, demo-focused Pulumi setup for deploying:

1. A GKE cluster with a GPU node pool
2. NVIDIA NIM Helm chart resources in that cluster
3. Commands to port-forward and test OpenAI-compatible chat completions via `curl`

The design intentionally mirrors your original imperative tutorial while moving core infrastructure and Kubernetes resources into Infrastructure as Code.

## What This Creates

### Infra stack (`nim-on-gke/infra`)

- GKE cluster:
  - Name: `nim-demo`
  - Zone: `us-east4-a`
  - Release channel: `RAPID`
  - Default node machine type: `e2-standard-4`
  - Default node count: `1`
- GPU node pool:
  - Name: `gpupool`
  - Machine type: `g2-standard-16`
  - GPU type/count: `nvidia-l4` x `1`
  - Node count: `1`

### Workloads stack (`nim-on-gke/workloads`)

- Namespace: `nim`
- Secret `registry-secret` for pulling private images from `nvcr.io`
- Secret `ngc-api` with `NGC_API_KEY` and `NGC_CLI_API_KEY`
- Helm release:
  - Release name: `my-nim`
  - Chart: `nim-llm` version `1.3.0`
  - Image: `nvcr.io/nim/meta/llama3-8b-instruct:1.0.0`
  - Persistence: enabled
- Helpful outputs:
  - `kubectl` commands for pod/service checks
  - Port-forward command
  - Ready-to-run `curl` command for chat completion

## Prerequisites

Install and authenticate these tools on your machine (or Cloud Shell):

- [Pulumi CLI](https://www.pulumi.com/docs/iac/download-install/)
- [Node.js](https://nodejs.org/) (18+ recommended)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) + `gke-gcloud-auth-plugin`
- A GCP project with billing enabled
- NVIDIA NGC API key

Enable APIs:

```bash
gcloud services enable container.googleapis.com compute.googleapis.com --project "$PROJECT_ID"
```

## Local Pulumi State

This setup uses a local filesystem backend (no Pulumi Cloud required) and keeps Pulumi metadata local to this directory:

```bash
cd /Users/brian/git/waywo/nim-on-gke
mkdir -p .pulumi-state .pulumi-home
export PULUMI_HOME="$PWD/.pulumi-home"
export PULUMI_CONFIG_PASSPHRASE="<choose-a-passphrase>"
pulumi login "file://$PWD/.pulumi-state"
```

## One-Time Environment Variables

```bash
export PROJECT_ID="<your-gcp-project-id>"
export REGION="us-east4"
export ZONE="us-east4-a"
export NGC_API_KEY="<your-ngc-api-key>"
```

`REGION` and `ZONE` are pinned in this demo to match your requested defaults.

## Option A: Deploy with Makefile (Recommended)

From `/Users/brian/git/waywo/nim-on-gke`:

```bash
make infra-up PROJECT_ID="$PROJECT_ID"
make workloads-up NGC_API_KEY="$NGC_API_KEY"
```

If you want to preview before apply:

```bash
make infra-preview PROJECT_ID="$PROJECT_ID"
make workloads-preview NGC_API_KEY="$NGC_API_KEY"
```

Inspect outputs:

```bash
make infra-output
make workloads-output
```

If your workloads deploy fails with `gke-gcloud-auth-plugin not found`, set the plugin path explicitly:

```bash
make workloads-up \
  NGC_API_KEY="$NGC_API_KEY" \
  AUTH_PLUGIN_COMMAND="$(which gke-gcloud-auth-plugin)"
```

## Option B: Deploy with Raw Pulumi CLI

### 1) Infra stack

```bash
cd /Users/brian/git/waywo/nim-on-gke/infra
npm install
export PULUMI_HOME="/Users/brian/git/waywo/nim-on-gke/.pulumi-home"
export PULUMI_CONFIG_PASSPHRASE="<choose-a-passphrase>"
pulumi stack select dev --create
pulumi config set projectId "$PROJECT_ID"
pulumi config set region "us-east4"
pulumi config set zone "us-east4-a"
pulumi config set clusterName "nim-demo"
pulumi config set clusterMachineType "e2-standard-4"
pulumi config set gpuNodePoolMachineType "g2-standard-16"
pulumi config set gpuType "nvidia-l4"
pulumi config set gpuCount "1"
pulumi up
```

### 2) Workloads stack

```bash
cd /Users/brian/git/waywo/nim-on-gke/workloads
npm install
export PULUMI_HOME="/Users/brian/git/waywo/nim-on-gke/.pulumi-home"
export PULUMI_CONFIG_PASSPHRASE="<choose-a-passphrase>"
pulumi stack select dev --create
pulumi config set infraStackRef "organization/nim-gke-infra/dev"
pulumi config set --secret ngcApiKey "$NGC_API_KEY"
pulumi config set authPluginCommand "$(which gke-gcloud-auth-plugin)"
pulumi config set useLoginShellWrapper "true"
pulumi up
```

## Configure kubectl

Use the command emitted by the infra stack:

```bash
cd /Users/brian/git/waywo/nim-on-gke/infra
export PULUMI_HOME="/Users/brian/git/waywo/nim-on-gke/.pulumi-home"
export PULUMI_CONFIG_PASSPHRASE="<choose-a-passphrase>"
pulumi stack output getCredentialsCommand
```

Run the printed command, for example:

```bash
gcloud container clusters get-credentials nim-demo --zone us-east4-a --project "$PROJECT_ID"
```

Then verify:

```bash
kubectl get nodes
kubectl get pods -n nim
kubectl get svc -n nim
```

## Port Forward and Test Inference

Start port forwarding in terminal 1:

```bash
kubectl port-forward service/my-nim-nim-llm 8000:8000 -n nim
```

In terminal 2, send an OpenAI-compatible chat completion request:

```bash
curl -X POST \
  "http://localhost:8000/v1/chat/completions" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
  "messages": [
    {
      "content": "You are a polite and respectful chatbot helping people plan a vacation.",
      "role": "system"
    },
    {
      "content": "What should I do for a 4 day vacation in Spain?",
      "role": "user"
    }
  ],
  "model": "meta/llama3-8b-instruct",
  "max_tokens": 128,
  "top_p": 1,
  "n": 1,
  "stream": false,
  "stop": "\n",
  "frequency_penalty": 0.0
}'
```

Nice! The inference is working. We are port forwarding to our NIM running in GKE on GCP!

```
~$ curl -X POST \
>   "http://localhost:8000/v1/chat/completions" \
>   -H "accept: application/json" \
>   -H "Content-Type: application/json" \
>   -d '{
>   "messages": [
>     {
>       "content": "You are a polite and respectful chatbot helping people plan a vacation.",
>       "role": "system"
>     },
>     {
>       "content": "What should I do for a 4 day vacation in Spain?",
>       "role": "user"
>     }
>   ],
>   "model": "meta/llama3-8b-instruct",
>   "max_tokens": 128,
>   "top_p": 1,
>   "n": 1,
>   "stream": false,
>   "stop": "\n",
>   "frequency_penalty": 0.0
> }'
{"id":"cmpl-9c11dd44b3784eeda34dab10b84dd1ec","object":"chat.completion","created":1771646528,"model":"meta/llama3-8b-instruct","choices":[{"index":0,"message":{"role":"assistant","content":"Spain! What a fantastic destination for a 4-day vacation! With so much to see and do, I'd be happy to help you plan your trip."},"logprobs":null,"finish_reason":"stop","stop_reason":"\n"}],"usage":{"prompt_tokens":42,"total_tokens":74,"completion_tokens":32}}~$
```


If the deployment is healthy and model initialization is complete, you should receive a valid chat completion JSON response.

## Cleanup

Destroy in reverse order (workloads first, then infra):

```bash
cd /Users/brian/git/waywo/nim-on-gke
make destroy
```

Equivalent raw commands:

```bash
cd /Users/brian/git/waywo/nim-on-gke/workloads
export PULUMI_HOME="/Users/brian/git/waywo/nim-on-gke/.pulumi-home"
export PULUMI_CONFIG_PASSPHRASE="<choose-a-passphrase>"
pulumi stack select dev
pulumi destroy --yes

cd /Users/brian/git/waywo/nim-on-gke/infra
export PULUMI_HOME="/Users/brian/git/waywo/nim-on-gke/.pulumi-home"
export PULUMI_CONFIG_PASSPHRASE="<choose-a-passphrase>"
pulumi stack select dev
pulumi destroy --yes
```

Optional local cleanup:

```bash
kubectl config delete-context "gke_${PROJECT_ID}_us-east4-a_nim-demo" || true
kubectl config delete-cluster "gke_${PROJECT_ID}_us-east4-a_nim-demo" || true
```

If you want to remove local Pulumi state files:

```bash
rm -rf /Users/brian/git/waywo/nim-on-gke/.pulumi-state
rm -rf /Users/brian/git/waywo/nim-on-gke/.pulumi-home
```

## Notes and Limitations

- This is intentionally minimal and demo-oriented:
  - No custom VPC setup
  - No IAM hardening beyond defaults
  - No production-grade autoscaling or policy controls
- For local filesystem Pulumi backends, stack references typically need the fixed organization prefix (`organization/...`).
- GPU quotas and availability vary by project/zone. If `pulumi up` fails due to quota/capacity, adjust machine/GPU settings.
- NIM startup may take several minutes while images/models initialize.

## Troubleshooting: gke-gcloud-auth-plugin Not Found

If you see an error like:

`exec: executable gke-gcloud-auth-plugin not found`

Run:

```bash
which gke-gcloud-auth-plugin
gke-gcloud-auth-plugin --version
```

If `which` is empty, install or expose the plugin in your PATH, then re-run workloads deploy.

If `which` succeeds but Pulumi still fails, set the absolute command path in stack config:

```bash
cd /Users/brian/git/waywo/nim-on-gke/workloads
export PULUMI_HOME="/Users/brian/git/waywo/nim-on-gke/.pulumi-home"
export PULUMI_CONFIG_PASSPHRASE="<choose-a-passphrase>"
pulumi config set authPluginCommand "$(which gke-gcloud-auth-plugin)"
pulumi config set useLoginShellWrapper "true"
pulumi up
```
