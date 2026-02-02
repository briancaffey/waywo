# Frontend

A modern web application built with Nuxt 4 and shadcn/ui components.

## Features

- **Modern UI**: Built with shadcn/ui components and Tailwind CSS
- **Responsive Design**: Mobile-first approach with responsive navigation
- **Professional Layout**: Clean, modern design with proper navigation
- **TypeScript Support**: Full TypeScript support with auto-imports
- **SEO Optimized**: Proper meta tags and page titles

## Pages

- **Home** (`/`): Landing page with hero section, features, and call-to-action

## Getting Started

1. Install dependencies:
   ```bash
   yarn
   ```

2. Start the development server:
   ```bash
   yarn dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
frontend/
├── app/
│   ├── app.vue          # Root app component
│   └── assets/
│       └── css/
│           └── tailwind.css
├── components/
│   └── ui/              # shadcn/ui components
├── layouts/
│   └── default.vue      # Default layout with navigation
├── pages/
│   ├── index.vue        # Home page
│   └── about.vue        # About page
├── lib/
│   └── utils.ts         # Utility functions
└── nuxt.config.ts       # Nuxt configuration
```

## Navigation

The default layout includes:
- **Navigation Links**: Home and About pages
- **Active State**: Current page is highlighted in the navigation
- **Mobile Menu**: Responsive hamburger menu for mobile devices
- **Footer**: Simple footer with copyright information

## Technologies Used

- **Nuxt 4**: Vue.js framework with SSR capabilities
- **shadcn/ui**: High-quality, accessible UI components
- **Tailwind CSS**: Utility-first CSS framework
- **TypeScript**: Type-safe JavaScript
- **Lucide Icons**: Beautiful, customizable icons