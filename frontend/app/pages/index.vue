<template>
  <div class="container mx-auto px-4 py-8">
    <!-- Hero Section -->
    <section class="text-center py-16">
      <div class="max-w-3xl mx-auto">
        <h1 class="text-4xl font-bold tracking-tight sm:text-6xl mb-6">
          what are you working on?
        </h1>
        <p class="text-xl text-muted-foreground mb-8">
          an application to explore what people are working on
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <NuxtLink to="/search">
            <Button size="lg" class="text-lg px-8">
              Search Projects
              <Icon name="lucide:search" class="ml-2 h-5 w-5" />
            </Button>
          </NuxtLink>
          <NuxtLink to="/posts">
            <Button variant="outline" size="lg" class="text-lg px-8">
              Browse Threads
            </Button>
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section class="py-16">
      <div class="text-center mb-12">
        <h2 class="text-3xl font-bold tracking-tight mb-4">Key Features</h2>
        <p class="text-lg text-muted-foreground">
          Discover and explore projects from Hacker News "What are you working on?" threads
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <Card class="p-6">
          <CardHeader>
            <div class="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Icon name="lucide:search" class="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Semantic Search</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-muted-foreground">
              Find projects by meaning, not just keywords. AI-powered vector embeddings let you search for concepts and ideas across all submissions.
            </p>
          </CardContent>
        </Card>

        <Card class="p-6">
          <CardHeader>
            <div class="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Icon name="lucide:message-circle" class="h-6 w-6 text-primary" />
            </div>
            <CardTitle>AI Chat Assistant</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-muted-foreground">
              Ask questions about projects in natural language. The RAG-powered chatbot retrieves relevant projects and provides informed answers.
            </p>
          </CardContent>
        </Card>

        <Card class="p-6">
          <CardHeader>
            <div class="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Icon name="lucide:sparkles" class="h-6 w-6 text-primary" />
            </div>
            <CardTitle>AI Project Extraction</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-muted-foreground">
              Projects are automatically extracted from HN comments using AI, with structured data including titles, descriptions, URLs, and scores.
            </p>
          </CardContent>
        </Card>

        <Card class="p-6">
          <CardHeader>
            <div class="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Icon name="lucide:filter" class="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Filter & Explore</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-muted-foreground">
              Browse and filter projects by hashtags, idea score, complexity score, and validity to find exactly what you're looking for.
            </p>
          </CardContent>
        </Card>

        <Card class="p-6">
          <CardHeader>
            <div class="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Icon name="lucide:calendar" class="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Monthly Threads</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-muted-foreground">
              Track Hacker News "What are you working on?" threads over time. See trends, browse by month, and explore what the community is building.
            </p>
          </CardContent>
        </Card>

        <Card class="p-6">
          <CardHeader>
            <div class="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Icon name="lucide:mic" class="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Voice Search</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-muted-foreground">
              Use real-time speech-to-text to search for projects and interact with the AI assistant hands-free via WebSocket streaming.
            </p>
          </CardContent>
        </Card>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="py-16">
      <Card class="p-8 text-center">
        <CardHeader>
          <CardTitle class="text-2xl mb-4">Ready to Explore?</CardTitle>
          <CardDescription class="text-lg">
            Ask the AI assistant about projects, or dive into the latest Hacker News threads.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div class="flex flex-col sm:flex-row gap-4 justify-center">
            <NuxtLink to="/chat">
              <Button size="lg" class="text-lg px-8">
                Chat with AI
                <Icon name="lucide:message-circle" class="ml-2 h-5 w-5" />
              </Button>
            </NuxtLink>
            <NuxtLink to="/posts">
              <Button variant="outline" size="lg" class="text-lg px-8">
                View Threads
              </Button>
            </NuxtLink>
          </div>
        </CardContent>
      </Card>
    </section>
  </div>
</template>
