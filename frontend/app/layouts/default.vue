<template>
  <div class="min-h-screen">
    <!-- Navigation Bar -->
    <nav class="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div class="container mx-auto px-4">
        <div class="flex h-16 items-center justify-between">
          <!-- Logo/Brand -->
          <div class="flex items-center space-x-2">
            <NuxtLink to="/" class="flex items-center space-x-2">
              <div class="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                <span class="text-primary-foreground font-bold text-sm">w</span>
              </div>
              <span class="text-xl font-bold">waywo</span>
            </NuxtLink>
          </div>

          <!-- Navigation Links -->
          <div class="hidden md:flex items-center space-x-6">
            <NuxtLink
              to="/posts"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/posts') ? 'text-primary' : 'text-muted-foreground'"
            >
              Posts
            </NuxtLink>
            <NuxtLink
              to="/comments"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/comments') ? 'text-primary' : 'text-muted-foreground'"
            >
              Comments
            </NuxtLink>
            <NuxtLink
              to="/projects"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/projects') ? 'text-primary' : 'text-muted-foreground'"
            >
              Projects
            </NuxtLink>
            <NuxtLink
              to="/explore"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/explore') ? 'text-primary' : 'text-muted-foreground'"
            >
              Explore
            </NuxtLink>
            <NuxtLink
              to="/videos"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/videos') ? 'text-primary' : 'text-muted-foreground'"
            >
              Videos
            </NuxtLink>
            <NuxtLink
              to="/search"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/search') ? 'text-primary' : 'text-muted-foreground'"
            >
              Search
            </NuxtLink>
            <NuxtLink
              to="/chat"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/chat') ? 'text-primary' : 'text-muted-foreground'"
            >
              Chat
            </NuxtLink>
            <NuxtLink
              to="/voice"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/voice') ? 'text-primary' : 'text-muted-foreground'"
            >
              Voice
            </NuxtLink>
            <NuxtLink
              to="/designer"
              class="text-sm font-medium transition-colors hover:text-primary" activeClass="" exactActiveClass=""
              :class="isActive('/designer') ? 'text-primary' : 'text-muted-foreground'"
            >
              Designer
            </NuxtLink>
            <button
              @click="toggleTheme"
              class="inline-flex items-center justify-center w-9 h-9 rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              style="cursor: pointer;"
            >
              <Icon
                :name="colorMode.value === 'dark' ? 'lucide:sun' : 'lucide:moon'"
                class="h-4 w-4 transition-transform duration-300 hover:scale-110"
                :class="colorMode.value === 'dark' ? 'rotate-180' : 'rotate-0'"
              />
            </button>
          </div>

          <!-- Mobile Menu Button -->
          <div class="md:hidden">
            <Button
              variant="ghost"
              size="sm"
              @click="mobileMenuOpen = !mobileMenuOpen"
            >
              <Icon name="lucide:menu" class="h-5 w-5" />
            </Button>
          </div>
        </div>

        <!-- Mobile Menu -->
        <div v-if="mobileMenuOpen" class="md:hidden border-t py-4">
          <div class="flex flex-col space-y-2">
            <NuxtLink
              to="/posts"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/posts') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Posts
            </NuxtLink>
            <NuxtLink
              to="/comments"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/comments') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Comments
            </NuxtLink>
            <NuxtLink
              to="/projects"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/projects') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Projects
            </NuxtLink>
            <NuxtLink
              to="/explore"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/explore') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Explore
            </NuxtLink>
            <NuxtLink
              to="/videos"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/videos') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Videos
            </NuxtLink>
            <NuxtLink
              to="/search"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/search') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Search
            </NuxtLink>
            <NuxtLink
              to="/chat"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/chat') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Chat
            </NuxtLink>
            <NuxtLink
              to="/voice"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/voice') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Voice
            </NuxtLink>
            <NuxtLink
              to="/designer"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md" activeClass="" exactActiveClass=""
              :class="isActive('/designer') ? 'text-primary bg-accent' : 'text-muted-foreground'"
              @click="mobileMenuOpen = false"
            >
              Designer
            </NuxtLink>
            <button
              @click="toggleTheme"
              class="inline-flex items-center justify-center w-9 h-9 rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <Icon
                :name="colorMode.value === 'dark' ? 'lucide:sun' : 'lucide:moon'"
                class="h-4 w-4"
              />
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-1">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="border-t bg-muted/40">
      <div class="container mx-auto px-4 py-12">
        <!-- Main Footer Grid -->
        <div class="grid grid-cols-2 gap-8 md:grid-cols-4 lg:grid-cols-5">
          <!-- Brand Column -->
          <div class="col-span-2 md:col-span-1 lg:col-span-2">
            <div class="flex items-center space-x-2 mb-4">
              <div class="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                <span class="text-primary-foreground font-bold text-sm">w</span>
              </div>
              <span class="text-lg font-bold">waywo</span>
            </div>
            <p class="text-sm text-muted-foreground leading-relaxed max-w-xs mb-4">
              Discover what people are building. AI-powered exploration of Hacker News "What are you working on?" threads.
            </p>
            <div class="flex items-center gap-3">
              <a
                href="https://news.ycombinator.com"
                target="_blank"
                rel="noopener noreferrer"
                class="text-muted-foreground hover:text-primary transition-colors"
                title="Hacker News"
              >
                <Icon name="lucide:newspaper" class="h-5 w-5" />
              </a>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                class="text-muted-foreground hover:text-primary transition-colors"
                title="GitHub"
              >
                <Icon name="lucide:github" class="h-5 w-5" />
              </a>
            </div>
          </div>

          <!-- Browse Column -->
          <div>
            <h3 class="text-sm font-semibold mb-3">Browse</h3>
            <ul class="space-y-2">
              <li>
                <NuxtLink to="/posts" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Monthly Threads
                </NuxtLink>
              </li>
              <li>
                <NuxtLink to="/comments" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Comments
                </NuxtLink>
              </li>
              <li>
                <NuxtLink to="/projects" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Projects
                </NuxtLink>
              </li>
              <li>
                <NuxtLink to="/explore" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Explore
                </NuxtLink>
              </li>
              <li>
                <NuxtLink to="/videos" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Videos
                </NuxtLink>
              </li>
            </ul>
          </div>

          <!-- Tools Column -->
          <div>
            <h3 class="text-sm font-semibold mb-3">Tools</h3>
            <ul class="space-y-2">
              <li>
                <NuxtLink to="/search" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Semantic Search
                </NuxtLink>
              </li>
              <li>
                <NuxtLink to="/chat" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  AI Chat
                </NuxtLink>
              </li>
              <li>
                <NuxtLink to="/voice" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Voice Assistant
                </NuxtLink>
              </li>
              <li>
                <NuxtLink to="/word-cloud" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Word Cloud
                </NuxtLink>
              </li>
              <li>
                <NuxtLink to="/designer" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Designer
                </NuxtLink>
              </li>
            </ul>
          </div>

          <!-- Resources Column -->
          <div>
            <h3 class="text-sm font-semibold mb-3">Resources</h3>
            <ul class="space-y-2">
              <li>
                <a
                  href="https://news.ycombinator.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-sm text-muted-foreground hover:text-primary transition-colors inline-flex items-center gap-1"
                >
                  Hacker News
                  <Icon name="lucide:external-link" class="h-3 w-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://news.ycombinator.com/item?id=42575537"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-sm text-muted-foreground hover:text-primary transition-colors inline-flex items-center gap-1"
                >
                  Latest WAYWO
                  <Icon name="lucide:external-link" class="h-3 w-3" />
                </a>
              </li>
              <li>
                <NuxtLink to="/admin" class="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Admin
                </NuxtLink>
              </li>
            </ul>
          </div>
        </div>

        <!-- Separator -->
        <div class="border-t mt-10 pt-6">
          <div class="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <p class="text-xs text-muted-foreground">
              Built with Nuxt, FastAPI & LlamaIndex. Data sourced from the Hacker News API.
            </p>
            <p class="text-xs text-muted-foreground">
              &copy; {{ new Date().getFullYear() }} waywo
            </p>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const mobileMenuOpen = ref(false)

// @ts-ignore - useColorMode is auto-imported by @nuxtjs/color-mode
const colorMode = useColorMode()

const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}

const toggleTheme = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
</script>
