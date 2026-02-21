import * as gcp from "@pulumi/gcp";
import * as pulumi from "@pulumi/pulumi";

const config = new pulumi.Config();

const projectId = config.require("projectId");
const regionConfig = config.get("region") ?? "us-east4";
const zoneConfig = config.get("zone") ?? "us-east4-a";
const clusterNameConfig = config.get("clusterName") ?? "nim-demo";
const clusterMachineType = config.get("clusterMachineType") ?? "e2-standard-4";
const clusterNodeCount = config.getNumber("clusterNodeCount") ?? 1;
const gpuNodePoolName = config.get("gpuNodePoolName") ?? "gpupool";
const gpuNodePoolMachineType = config.get("gpuNodePoolMachineType") ?? "g2-standard-16";
const gpuType = config.get("gpuType") ?? "nvidia-l4";
const gpuCount = config.getNumber("gpuCount") ?? 1;
const gpuNodeCount = config.getNumber("gpuNodeCount") ?? 1;

const cluster = new gcp.container.Cluster(clusterNameConfig, {
    name: clusterNameConfig,
    project: projectId,
    location: zoneConfig,
    deletionProtection: false,
    initialNodeCount: clusterNodeCount,
    releaseChannel: {
        channel: "RAPID",
    },
    nodeConfig: {
        machineType: clusterMachineType,
        oauthScopes: ["https://www.googleapis.com/auth/cloud-platform"],
    },
});

const gpuNodePool = new gcp.container.NodePool(gpuNodePoolName, {
    name: gpuNodePoolName,
    project: projectId,
    location: zoneConfig,
    cluster: cluster.name,
    nodeCount: gpuNodeCount,
    nodeConfig: {
        machineType: gpuNodePoolMachineType,
        oauthScopes: ["https://www.googleapis.com/auth/cloud-platform"],
        guestAccelerators: [{
            type: gpuType,
            count: gpuCount,
            gpuDriverInstallationConfig: {
                gpuDriverVersion: "LATEST",
            },
        }],
    },
}, { dependsOn: [cluster] });

const contextName = pulumi.interpolate`gke_${projectId}_${zoneConfig}_${cluster.name}`;
const clusterCaCertificate = cluster.masterAuth.apply((auth) => auth.clusterCaCertificate);

const renderedKubeconfig = pulumi.all([cluster.endpoint, clusterCaCertificate, contextName]).apply(
    ([endpoint, ca, context]) => `apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: ${ca}
    server: https://${endpoint}
  name: ${context}
contexts:
- context:
    cluster: ${context}
    user: ${context}
  name: ${context}
current-context: ${context}
kind: Config
preferences: {}
users:
- name: ${context}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin and configure gcloud credentials.
      provideClusterInfo: true
`,
);

const renderedGetCredentialsCommand = pulumi.interpolate`gcloud container clusters get-credentials ${cluster.name} --zone ${zoneConfig} --project ${projectId}`;

export const gcpProjectId = projectId;
export const regionOutput = regionConfig;
export const zoneOutput = zoneConfig;
export const clusterNameOutput = cluster.name;
export const clusterEndpoint = cluster.endpoint;
export const gpuNodePoolNameOutput = gpuNodePool.name;
export const kubeconfigOutput = pulumi.secret(renderedKubeconfig);
export const getCredentialsCommandOutput = renderedGetCredentialsCommand;

// Backward-compatible output aliases for stack references and easy CLI usage.
export const zone = zoneOutput;
export const clusterName = clusterNameOutput;
export const kubeconfig = kubeconfigOutput;
export const getCredentialsCommand = getCredentialsCommandOutput;
