# Frontend Architecture - FastAPI Static Serving (HealthHub supplement)

> Supplements base [Architecture](../../../../documents/engineering/architecture.md). Base layer rules apply; see `architecture.md` overlay for canonical HealthHub deltas.

## Overview

HealthHub uses a **single-server architecture** where FastAPI serves both the REST API and the React frontend application. This document describes the frontend serving pattern, build process, and development workflows.

## Pattern: FastAPI StaticFiles + Catch-All Route

### Architecture

```
Request Flow:
1. Browser → http://localhost:8850/
2. FastAPI checks registered routes:
   - /api/* → API routers (FastAPI route handlers)
   - /health → Health check endpoint
   - /static/* → StaticFiles (JS, CSS, images)
   - /* → Catch-all (serves index.html)
3. React Router takes over client-side navigation
```

### Implementation

**Location**: `backend/app/main.py` (lines ~75-100)

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Mount static assets
frontend_build_path = Path("/opt/healthhub/frontend-build/build")
if frontend_build_path.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(frontend_build_path / "static")),
        name="static",
    )

    # Catch-all for React Router
    @app.get("/{full_path:path}", response_model=None)
    async def serve_react_app(request: Request, full_path: str):
        if full_path.startswith("api/") or full_path.startswith("health"):
            return JSONResponse({"error": "Not found"}, status_code=404)

        index_file = frontend_build_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

        return JSONResponse({"error": "Frontend not built"}, status_code=503)
```

### Why This Pattern?

**Benefits**:
- ✅ Single port (8850) for entire application
- ✅ No CORS issues (same origin)
- ✅ Simplified deployment (one container)
- ✅ Production-ready by default
- ✅ Matches reference architecture (ShipNorth)

**Trade-offs**:
- ⚠️ Frontend changes require Docker rebuild (or local dev server)
- ⚠️ No hot module replacement (HMR) in Docker

---

## Build Process

### Docker Build Stages

**Location**: `docker/Dockerfile` (lines ~100-115)

```dockerfile
# Step 3: Build Frontend
COPY demo/healthhub/frontend/package.json demo/healthhub/frontend/package-lock.json /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/src /opt/healthhub/frontend-build/src
COPY demo/healthhub/frontend/public /opt/healthhub/frontend-build/public
COPY demo/healthhub/frontend/index.html /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/vite.config.ts /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/tsconfig.json /opt/healthhub/frontend-build/

WORKDIR /opt/healthhub/frontend-build
RUN npm ci --quiet && \
    BUILD_PATH=build npm run build && \
    ls -la build/index.html
```

### Build Output Structure

```
/opt/healthhub/frontend-build/build/
├── index.html                    # SPA entry point
├── static/
│   ├── js/
│   │   ├── main.[hash].js       # React app bundle
│   │   └── vendor.[hash].js     # Dependencies bundle
│   ├── css/
│   │   └── main.[hash].css      # Compiled styles
│   └── media/                    # Images, fonts, etc.
└── manifest.json
```

### Build Configuration

**Vite Config**: `frontend/vite.config.ts`

```typescript
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'build',  // Match ShipNorth pattern (not 'dist')
  },
  // ... server config for local dev
})
```

---

## Development Workflows

### Workflow 1: Backend Development Only

**Use case**: Modifying API routes, effect programs, interpreters

```bash
# Start services
docker compose -f docker/docker-compose.yml up -d

# Backend hot reload is enabled (uvicorn --reload)
# Edit files in backend/app/
# Changes reload automatically

# Access app at http://localhost:8850
```

**No frontend rebuild needed** - uses embedded frontend from Docker build.

---

### Workflow 2: Frontend Development (Local Vite Server)

**Use case**: Modifying React components, styles, frontend logic

```bash
# Terminal 1: Start backend in Docker
docker compose -f docker/docker-compose.yml up -d

# Terminal 2: Run Vite dev server locally
cd demo/healthhub/frontend
npm install  # First time only
npm run dev

# Access frontend at http://localhost:5173 (with HMR)
# API proxied to http://localhost:8850 (via vite.config.ts)
```

**Benefits**: Hot module replacement, instant feedback on changes.

---

### Workflow 3: Full Stack Development (Rebuild)

**Use case**: Testing integrated frontend + backend changes

```bash
# Rebuild healthhub container with new frontend build
docker compose -f docker/docker-compose.yml build healthhub

# Restart services
docker compose -f docker/docker-compose.yml up -d

# Access app at http://localhost:8850
```

**When to use**: Before committing, testing production build, E2E tests.

---

## Routing

### FastAPI Route Registration Order

**Critical**: Route order matters for catch-all pattern.

```python
# 1. API routes registered first (highest priority)
app.include_router(health_router, tags=["health"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(patients_router, prefix="/api/patients", tags=["patients"])
# ... other API routers

# 2. Static files mount (second priority)
app.mount("/static", StaticFiles(...), name="static")

# 3. Catch-all for React Router (lowest priority)
@app.get("/{full_path:path}")
async def serve_react_app(...):
    # Only reaches here if no other route matched
```

### React Router Client-Side Routing

**Location**: `frontend/src/App.tsx`

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/patients" element={<PatientsPage />} />
        {/* ... other routes */}
      </Routes>
    </BrowserRouter>
  );
}
```

**How it works**:
1. User navigates to `/patients`
2. FastAPI catch-all serves `index.html`
3. React loads, React Router sees `/patients` in URL
4. React Router renders `<PatientsPage />`

---

## Testing

### Backend Tests (Unaffected)

```bash
# Unit tests (pytest-mock, no I/O)
docker compose -f docker/docker-compose.yml exec healthhub poetry run test-backend

# Integration tests (real PostgreSQL/Redis/Pulsar)
docker compose -f docker/docker-compose.yml exec healthhub poetry run test-integration
```

**Frontend serving does not affect backend tests** - they test effect programs and interpreters directly.

### Frontend Testing (Future)

**Potential approaches**:
1. Vitest unit tests (components in isolation)
2. Playwright E2E tests (full browser testing)
3. Integration tests with real backend

**Not currently implemented** - focus is on backend effect system.

---

## Troubleshooting

### Frontend Not Loading (503 Error)

**Symptom**: Accessing http://localhost:8850 returns `{"error": "Frontend not built"}`

**Cause**: Frontend build didn't complete during Docker build.

**Solution**:
```bash
# Rebuild with frontend
docker compose -f docker/docker-compose.yml build healthhub

# Check build logs for errors
docker compose -f docker/docker-compose.yml logs healthhub | grep "frontend-build"
```

---

### API Routes Returning 404

**Symptom**: `/api/auth/login` returns 404 instead of proper error.

**Cause**: Catch-all route intercepting API routes.

**Solution**: Verify route registration order in `main.py` - API routers MUST be registered before catch-all.

---

### Static Assets Not Loading (404)

**Symptom**: Browser console shows 404 for `/static/js/main.[hash].js`

**Cause**: StaticFiles mount path mismatch.

**Solution**: Verify Vite build output structure matches StaticFiles mount:
```bash
docker compose -f docker/docker-compose.yml exec healthhub ls -la /opt/healthhub/frontend-build/build/static/
```

---

## Security Considerations

### Content Security Policy (Future)

**Not currently implemented** - consider adding CSP headers:

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        # ... other directives
    )
    return response
```

**Reference**: ShipNorth `server.py` lines 321-349.

---

## References

- **ShipNorth Pattern**: `~/shipnorth/backend/api/server.py` (reference implementation)
- **FastAPI StaticFiles**: https://fastapi.tiangolo.com/tutorial/static-files/
- **Vite Build**: https://vitejs.dev/guide/build.html
- **React Router**: https://reactrouter.com/en/main/start/tutorial

---

## Related Documentation

### Domain Knowledge
- N/A (frontend is not healthcare-specific)

### Engineering Patterns
- [Effect Patterns](effect_patterns.md) - Backend effect programs that power the API
- [Testing](testing.md) - Backend testing strategies

### Product Documentation
- [Architecture Overview](../product/architecture_overview.md) - 5-layer backend architecture
- [API Reference](../product/api_reference.md) - REST endpoints consumed by frontend

### Tutorials
- [Quickstart](../tutorials/01_quickstart.md) - Getting started guide includes frontend access

---

**SSoT Status**: This document is the Single Source of Truth for frontend architecture in HealthHub.
**Last Updated**: 2025-11-28
**Supersedes**: none
**Related Files**:
- `backend/app/main.py` - Frontend serving implementation
- `frontend/vite.config.ts` - Build configuration
- `docker/Dockerfile` - Frontend build steps
- `../CLAUDE.md` - Development commands and workflows  
**Referenced by**: README.md, architecture.md
