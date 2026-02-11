<template>
  <div class="min-h-screen bg-background">
    <!-- Navigation Bar -->
    <nav class="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div class="container mx-auto px-4">
        <div class="flex h-16 items-center justify-between">
          <!-- Logo/Brand -->
          <div class="flex items-center space-x-2">
            <a href="/" class="flex items-center space-x-2">
              <div class="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                <span class="text-primary-foreground font-bold text-sm">w</span>
              </div>
              <span class="text-xl font-bold">waywo</span>
            </a>
          </div>

          <!-- Navigation Links -->
          <div class="hidden md:flex items-center space-x-6">
            <a
              href="/posts"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/posts') ? 'text-primary' : 'text-muted-foreground'"
            >
              Posts
            </a>
            <a
              href="/comments"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/comments') ? 'text-primary' : 'text-muted-foreground'"
            >
              Comments
            </a>
            <a
              href="/projects"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/projects') ? 'text-primary' : 'text-muted-foreground'"
            >
              Projects
            </a>
            <a
              href="/explore"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/explore') ? 'text-primary' : 'text-muted-foreground'"
            >
              Explore
            </a>
            <a
              href="/word-cloud"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/word-cloud') ? 'text-primary' : 'text-muted-foreground'"
            >
              Word Cloud
            </a>
            <a
              href="/videos"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/videos') ? 'text-primary' : 'text-muted-foreground'"
            >
              Videos
            </a>
            <a
              href="/search"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/search') ? 'text-primary' : 'text-muted-foreground'"
            >
              Search
            </a>
            <a
              href="/chat"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/chat') ? 'text-primary' : 'text-muted-foreground'"
            >
              Chat
            </a>
            <a
              href="/voice"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/voice') ? 'text-primary' : 'text-muted-foreground'"
            >
              Voice
            </a>
            <a
              href="/designer"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/designer') ? 'text-primary' : 'text-muted-foreground'"
            >
              Designer
            </a>
            <a
              href="/admin"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="isActive('/admin') ? 'text-primary' : 'text-muted-foreground'"
            >
              Admin
            </a>
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
            <a
              href="/posts"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/posts') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Posts
            </a>
            <a
              href="/comments"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/comments') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Comments
            </a>
            <a
              href="/projects"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/projects') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Projects
            </a>
            <a
              href="/explore"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/explore') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Explore
            </a>
            <a
              href="/word-cloud"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/word-cloud') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Word Cloud
            </a>
            <a
              href="/videos"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/videos') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Videos
            </a>
            <a
              href="/search"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/search') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Search
            </a>
            <a
              href="/chat"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/chat') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Chat
            </a>
            <a
              href="/voice"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/voice') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Voice
            </a>
            <a
              href="/designer"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/designer') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Designer
            </a>
            <a
              href="/admin"
              class="text-sm font-medium transition-colors hover:text-primary px-2 py-1 rounded-md"
              :class="isActive('/admin') ? 'text-primary bg-accent' : 'text-muted-foreground'"
            >
              Admin
            </a>
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
    <footer class="border-t bg-background">
      <div class="container mx-auto px-4 py-8">
        <div class="flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
          <div class="flex flex-col items-center gap-4 px-8 md:flex-row md:gap-2 md:px-0">
            <p class="text-center text-sm leading-loose text-muted-foreground md:text-left">
              waywo
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
