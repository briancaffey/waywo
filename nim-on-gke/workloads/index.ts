import * as k8s from "@pulumi/kubernetes";
import * as pulumi from "@pulumi/pulumi";

const config = new pulumi.Config();

const infraStackRefInput = config.require("infraStackRef");
const ngcApiKey = config.requireSecret("ngcApiKey");
const authPluginCommand = config.get("authPluginCommand") ?? "gke-gcloud-auth-plugin";
const useLoginShellWrapper = config.getBoolean("useLoginShellWrapper") ?? true;

// Local Pulumi backends use a fixed organization segment: "organization".
// Accept both "project/stack" and full "organization/project/stack".
const infraStackRefName = infraStackRefInput.split("/").length === 2
    ? `organization/${infraStackRefInput}`
    : infraStackRefInput;

const infra = new pulumi.StackReference(infraStackRefName);

function escapeSingleQuotes(value: string): string {
    return value.replace(/'/g, "'\"'\"'");
}

const kubeconfig = infra.requireOutput("kubeconfig").apply((raw) => {
    const rawKubeconfig = raw as string;
    const commandPattern = /command:\s*gke-gcloud-auth-plugin/g;

    if (!commandPattern.test(rawKubeconfig)) {
        return rawKubeconfig;
    }

    if (!useLoginShellWrapper) {
        return rawKubeconfig.replace(commandPattern, `command: ${authPluginCommand}`);
    }

    const escapedCommand = escapeSingleQuotes(authPluginCommand);
    return rawKubeconfig.replace(
        commandPattern,
        `command: /bin/bash
      args:
      - -lc
      - '${escapedCommand}'`,
    );
});

const provider = new k8s.Provider("gke-provider", {
    kubeconfig,
});

const namespace = new k8s.core.v1.Namespace("nim-namespace", {
    metadata: {
        name: "nim",
    },
}, { provider });

const registrySecret = new k8s.core.v1.Secret("registry-secret", {
    metadata: {
        name: "registry-secret",
        namespace: namespace.metadata.name,
    },
    type: "kubernetes.io/dockerconfigjson",
    stringData: {
        ".dockerconfigjson": ngcApiKey.apply((key) => {
            const auth = Buffer.from(`$oauthtoken:${key}`).toString("base64");
            return JSON.stringify({
                auths: {
                    "nvcr.io": {
                        username: "$oauthtoken",
                        password: key,
                        auth,
                    },
                },
            });
        }),
    },
}, { provider });

const ngcApiSecret = new k8s.core.v1.Secret("ngc-api", {
    metadata: {
        name: "ngc-api",
        namespace: namespace.metadata.name,
    },
    type: "Opaque",
    stringData: {
        NGC_API_KEY: ngcApiKey,
        NGC_CLI_API_KEY: ngcApiKey,
    },
}, { provider });

const releaseName = "my-nim";
const chartName = "nim-llm";
const chartVersion = "1.3.0";
const serviceName = `${releaseName}-${chartName}`;

const nimRelease = new k8s.helm.v3.Release("nim-llm-release", {
    name: releaseName,
    namespace: namespace.metadata.name,
    chart: chartName,
    version: chartVersion,
    repositoryOpts: {
        repo: "https://helm.ngc.nvidia.com/nim",
        username: "$oauthtoken",
        password: ngcApiKey,
    },
    values: {
        image: {
            repository: "nvcr.io/nim/meta/llama3-8b-instruct",
            tag: "1.0.0",
        },
        model: {
            ngcAPISecret: "ngc-api",
        },
        persistence: {
            enabled: true,
        },
        imagePullSecrets: [{
            name: "registry-secret",
        }],
    },
    timeout: 1800,
}, { provider, dependsOn: [registrySecret, ngcApiSecret] });

const renderedPortForwardCommand = pulumi.interpolate`kubectl port-forward service/${serviceName} 8000:8000 -n ${namespace.metadata.name}`;

const curlRequestBody = `{
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
  "stop": "\\n",
  "frequency_penalty": 0.0
}`;

const renderedCurlCommand = `curl -X POST \\
  "http://localhost:8000/v1/chat/completions" \\
  -H "accept: application/json" \\
  -H "Content-Type: application/json" \\
  -d '${curlRequestBody}'`;

export const infraStackReference = infraStackRefName;
export const namespaceName = namespace.metadata.name;
export const helmReleaseName = nimRelease.name;
export const nimServiceName = serviceName;
export const listPodsCommand = pulumi.interpolate`kubectl get pods -n ${namespace.metadata.name}`;
export const listServicesCommand = pulumi.interpolate`kubectl get svc -n ${namespace.metadata.name}`;
export const portForwardCommandOutput = renderedPortForwardCommand;
export const curlCommandOutput = renderedCurlCommand;

// Backward-compatible output aliases for easy CLI usage.
export const portForwardCommand = portForwardCommandOutput;
export const curlCommand = curlCommandOutput;
