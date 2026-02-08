<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-6xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:scatter-chart" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Explore</h1>
        <p class="text-xl text-muted-foreground">
          Explore project clusters visualized with UMAP dimensionality reduction
        </p>
      </div>

      <!-- Stats Summary -->
      <div v-if="clusterMap" class="grid grid-cols-2 gap-4 max-w-sm mx-auto mb-8">
        <div class="p-4 bg-muted rounded-lg text-center">
          <p class="text-2xl font-bold">{{ clusterMap.total.value }}</p>
          <p class="text-sm text-muted-foreground">Projects</p>
        </div>
        <div class="p-4 bg-muted rounded-lg text-center">
          <p class="text-2xl font-bold">{{ clusterMap.clusterCount.value }}</p>
          <p class="text-sm text-muted-foreground">Clusters</p>
        </div>
      </div>

      <!-- Cluster Map -->
      <Card class="p-6">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-lg font-semibold">Project Cluster Map</h2>
            <p class="text-sm text-muted-foreground">
              Hover to see details, click to open a project
            </p>
          </div>
          <Button variant="outline" size="sm" @click="clusterMap?.refresh()">
            <Icon name="lucide:refresh-cw" class="h-4 w-4" />
          </Button>
        </div>
        <WaywoClusterMap ref="clusterMap" />
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
useHead({
  title: 'Explore - waywo',
  meta: [
    { name: 'description', content: 'Explore project clusters with interactive UMAP visualization.' }
  ]
})

const clusterMap = ref<InstanceType<typeof WaywoClusterMap> | null>(null)
</script>
