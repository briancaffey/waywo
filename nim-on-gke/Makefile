SHELL := /usr/bin/env bash

ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
BACKEND_DIR ?= $(ROOT_DIR)/.pulumi-state
PULUMI_BACKEND_URL ?= file://$(BACKEND_DIR)
PULUMI_HOME ?= $(ROOT_DIR)/.pulumi-home
PULUMI_SECRETS_PASSPHRASE ?= nim-on-gke-demo-passphrase
PULUMI := PULUMI_HOME="$(PULUMI_HOME)" PULUMI_CONFIG_PASSPHRASE="$(PULUMI_SECRETS_PASSPHRASE)" pulumi

INFRA_DIR := $(ROOT_DIR)/infra
WORKLOADS_DIR := $(ROOT_DIR)/workloads

INFRA_STACK ?= dev
WORKLOADS_STACK ?= dev
INFRA_STACK_REF ?= organization/nim-gke-infra/$(INFRA_STACK)

PROJECT_ID ?=
NGC_API_KEY ?=
AUTH_PLUGIN_COMMAND ?= gke-gcloud-auth-plugin
USE_LOGIN_SHELL_WRAPPER ?= true

.PHONY: help login deps infra-stack infra-config infra-preview infra-up infra-output \
	workloads-stack workloads-config workloads-preview workloads-up workloads-output \
	get-credentials port-forward print-curl workloads-destroy infra-destroy destroy

help:
	@echo "Targets:"
	@echo "  make login              - Pulumi login using local filesystem backend"
	@echo "  make deps               - Install npm dependencies for both Pulumi projects"
	@echo "  make infra-up           - Configure + deploy GKE cluster and GPU node pool"
	@echo "  make workloads-up       - Configure + deploy NIM namespace, secrets, and Helm release"
	@echo "  make infra-output       - Show infra stack outputs"
	@echo "  make workloads-output   - Show workloads stack outputs"
	@echo "  make get-credentials    - Print gcloud command to configure kubectl"
	@echo "  make port-forward       - Print kubectl port-forward command"
	@echo "  make print-curl         - Print sample curl chat completion command"
	@echo "  make destroy            - Destroy workloads then infrastructure"
	@echo ""
	@echo "Required variables:"
	@echo "  PROJECT_ID=<gcp-project-id> (for infra-* targets)"
	@echo "  NGC_API_KEY=<ngc-api-key> (for workloads-* targets)"
	@echo ""
	@echo "Optional variables:"
	@echo "  PULUMI_SECRETS_PASSPHRASE=<value> (defaults to demo passphrase)"
	@echo "  AUTH_PLUGIN_COMMAND=<path-or-command> (defaults to gke-gcloud-auth-plugin)"
	@echo "  USE_LOGIN_SHELL_WRAPPER=<true|false> (defaults to true)"

require-project-id:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "PROJECT_ID is required. Example: make infra-up PROJECT_ID=my-gcp-project"; \
		exit 1; \
	fi

require-ngc-api-key:
	@if [ -z "$(NGC_API_KEY)" ]; then \
		echo "NGC_API_KEY is required. Example: make workloads-up NGC_API_KEY=..."; \
		exit 1; \
	fi

login:
	@mkdir -p "$(BACKEND_DIR)"
	@mkdir -p "$(PULUMI_HOME)"
	$(PULUMI) login "$(PULUMI_BACKEND_URL)"

deps:
	cd "$(INFRA_DIR)" && npm install
	cd "$(WORKLOADS_DIR)" && npm install

infra-stack: login
	cd "$(INFRA_DIR)" && $(PULUMI) stack select "$(INFRA_STACK)" --create

infra-config: require-project-id infra-stack
	cd "$(INFRA_DIR)" && $(PULUMI) config set projectId "$(PROJECT_ID)"
	cd "$(INFRA_DIR)" && $(PULUMI) config set region "us-east4"
	cd "$(INFRA_DIR)" && $(PULUMI) config set zone "us-east4-a"
	cd "$(INFRA_DIR)" && $(PULUMI) config set clusterName "nim-demo"
	cd "$(INFRA_DIR)" && $(PULUMI) config set clusterMachineType "e2-standard-4"
	cd "$(INFRA_DIR)" && $(PULUMI) config set gpuNodePoolMachineType "g2-standard-16"
	cd "$(INFRA_DIR)" && $(PULUMI) config set gpuType "nvidia-l4"
	cd "$(INFRA_DIR)" && $(PULUMI) config set gpuCount "1"

infra-preview: deps infra-config
	cd "$(INFRA_DIR)" && $(PULUMI) preview

infra-up: deps infra-config
	cd "$(INFRA_DIR)" && $(PULUMI) up

infra-output:
	cd "$(INFRA_DIR)" && $(PULUMI) stack output

workloads-stack: login
	cd "$(WORKLOADS_DIR)" && $(PULUMI) stack select "$(WORKLOADS_STACK)" --create

workloads-config: require-ngc-api-key workloads-stack
	cd "$(WORKLOADS_DIR)" && $(PULUMI) config set infraStackRef "$(INFRA_STACK_REF)"
	cd "$(WORKLOADS_DIR)" && $(PULUMI) config set --secret ngcApiKey "$(NGC_API_KEY)"
	cd "$(WORKLOADS_DIR)" && $(PULUMI) config set authPluginCommand "$(AUTH_PLUGIN_COMMAND)"
	cd "$(WORKLOADS_DIR)" && $(PULUMI) config set useLoginShellWrapper "$(USE_LOGIN_SHELL_WRAPPER)"

workloads-preview: deps workloads-config
	cd "$(WORKLOADS_DIR)" && $(PULUMI) preview

workloads-up: deps workloads-config
	cd "$(WORKLOADS_DIR)" && $(PULUMI) up

workloads-output:
	cd "$(WORKLOADS_DIR)" && $(PULUMI) stack output

get-credentials:
	cd "$(INFRA_DIR)" && $(PULUMI) stack output getCredentialsCommand

port-forward:
	cd "$(WORKLOADS_DIR)" && $(PULUMI) stack output portForwardCommand

print-curl:
	cd "$(WORKLOADS_DIR)" && $(PULUMI) stack output curlCommand

workloads-destroy: workloads-stack
	cd "$(WORKLOADS_DIR)" && $(PULUMI) destroy --yes

infra-destroy: infra-stack
	cd "$(INFRA_DIR)" && $(PULUMI) destroy --yes

destroy: workloads-destroy infra-destroy
