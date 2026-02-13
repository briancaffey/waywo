<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-6xl mx-auto">
      <WaywoPageHeader
        icon="lucide:scatter-chart"
        title="Explore"
        description="Explore project clusters visualized with UMAP dimensionality reduction"
      />

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
