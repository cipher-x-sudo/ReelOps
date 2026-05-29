import React, { useEffect, useMemo, useState } from "react"
import { createRoot } from "react-dom/client"
import "./styles.css"

type Workspace = { id: string; name: string; slug: string }
type Role = { id: string; name: string; permissions: string[]; is_system: boolean; description: string; workspace_id: string }
type User = { id: string; email: string; name: string; is_active: boolean; created_at: string }
type Membership = { workspace: Workspace; role: Role }
type Me = { user: User; memberships: Membership[] }
type Niche = { id: string; title: string; slug: string; needs_review: boolean; source_type: string; config: Record<string, any> }
type Job = {
  id: string
  title: string
  status: string
  current_step: string
  language: string
  platform: string
  payload: Record<string, any>
  artifacts: Record<string, any>
  created_at: string
}

const API = ""

async function request<T>(path: string, token: string, workspaceId: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set("Content-Type", "application/json")
  if (token) headers.set("Authorization", `Bearer ${token}`)
  if (workspaceId) headers.set("X-Workspace-Id", workspaceId)
  const response = await fetch(`${API}${path}`, { ...init, headers })
  if (!response.ok) throw new Error(await response.text())
  return response.json()
}

function useLocalToken() {
  const [token, setTokenState] = useState(() => localStorage.getItem("reelops.token") || "")
  const setToken = (value: string) => {
    localStorage.setItem("reelops.token", value)
    setTokenState(value)
  }
  const clear = () => {
    localStorage.removeItem("reelops.token")
    setTokenState("")
  }
  return { token, setToken, clear }
}

function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState("owner@reelops.app")
  const [password, setPassword] = useState("change-me-now")
  const [error, setError] = useState("")
  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError("")
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      })
      if (!response.ok) throw new Error(await response.text())
      const data = await response.json()
      onLogin(data.access_token)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed")
    }
  }
  return (
    <main className="login">
      <section className="login-panel">
        <p className="eyebrow">ReelOps</p>
        <h1>Sign in to the reel factory</h1>
        <form onSubmit={submit} className="form-stack">
          <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          {error ? <pre className="error">{error}</pre> : null}
          <button>Sign in</button>
        </form>
      </section>
    </main>
  )
}

function Dashboard({ token, clear }: { token: string; clear: () => void }) {
  const [me, setMe] = useState<Me | null>(null)
  const [workspaceId, setWorkspaceId] = useState("")
  const [roles, setRoles] = useState<Role[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [niches, setNiches] = useState<Niche[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedNiche, setSelectedNiche] = useState("")
  const [jobTitle, setJobTitle] = useState("")
  const [language, setLanguage] = useState("English")
  const [platform, setPlatform] = useState("multi-platform")
  const [newUser, setNewUser] = useState({ email: "", name: "", password: "", role_id: "" })
  const [notice, setNotice] = useState("")

  const membership = useMemo(() => me?.memberships.find((m) => m.workspace.id === workspaceId), [me, workspaceId])
  const permissions = new Set(membership?.role.permissions || [])
  const can = (permission: string) => permissions.has("*") || permissions.has(permission)

  async function refresh(nextWorkspace = workspaceId) {
    const profile = await request<Me>("/api/auth/me", token, nextWorkspace)
    setMe(profile)
    const ws = nextWorkspace || profile.memberships[0]?.workspace.id || ""
    setWorkspaceId(ws)
    const [roleRows, nicheRows, jobRows] = await Promise.all([
      request<Role[]>("/api/roles", token, ws),
      request<Niche[]>("/api/reels/niches", token, ws),
      request<Job[]>("/api/reels/jobs", token, ws)
    ])
    setRoles(roleRows)
    setNiches(nicheRows)
    setJobs(jobRows)
    if (roleRows[0] && !newUser.role_id) setNewUser((old) => ({ ...old, role_id: roleRows[0].id }))
    if (can("users.manage")) {
      try {
        setUsers(await request<User[]>("/api/users", token, ws))
      } catch {
        setUsers([])
      }
    }
  }

  useEffect(() => {
    refresh().catch((err) => setNotice(err.message))
  }, [])

  async function importNiches() {
    setNotice("Importing niches...")
    const rows = await request<Niche[]>("/api/reels/niches/import", token, workspaceId, { method: "POST" })
    setNiches(rows)
    setNotice(`Imported ${rows.length} niches.`)
  }

  async function createJob(event: React.FormEvent) {
    event.preventDefault()
    const job = await request<Job>("/api/reels/jobs", token, workspaceId, {
      method: "POST",
      body: JSON.stringify({ niche_id: selectedNiche, title: jobTitle, platform, language, options: {} })
    })
    setJobs([job, ...jobs])
    setNotice(`Created job ${job.title}.`)
  }

  async function jobAction(job: Job, action: "advance" | "approve" | "render") {
    const body =
      action === "approve"
        ? { step_key: job.current_step, decision: "approved", notes: "Approved in dashboard." }
        : action === "advance"
          ? { input: {} }
          : {}
    const updated = await request<Job>(`/api/reels/jobs/${job.id}/${action}`, token, workspaceId, {
      method: "POST",
      body: JSON.stringify(body)
    })
    setJobs((rows) => rows.map((row) => (row.id === updated.id ? updated : row)))
    setNotice(`${action} complete for ${updated.title}.`)
  }

  async function createUser(event: React.FormEvent) {
    event.preventDefault()
    const created = await request<User>("/api/users", token, workspaceId, {
      method: "POST",
      body: JSON.stringify({ ...newUser, workspace_id: workspaceId })
    })
    setUsers([created, ...users])
    setNewUser({ email: "", name: "", password: "", role_id: roles[0]?.id || "" })
    setNotice(`Created user ${created.email}.`)
  }

  return (
    <main className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">ReelOps</p>
          <h1>Production dashboard</h1>
        </div>
        <div className="topbar-actions">
          <select value={workspaceId} onChange={(e) => refresh(e.target.value)}>
            {me?.memberships.map((m) => <option key={m.workspace.id} value={m.workspace.id}>{m.workspace.name}</option>)}
          </select>
          <span className="pill">{membership?.role.name || "Role"}</span>
          <button className="ghost" onClick={clear}>Sign out</button>
        </div>
      </header>

      {notice ? <div className="notice">{notice}</div> : null}

      <section className="grid">
        <article className="panel span-2">
          <div className="panel-head">
            <div>
              <h2>New reel job</h2>
              <p>Choose a niche, platform, and language. Every step remains editable.</p>
            </div>
            {can("niches.manage") ? <button className="ghost" onClick={importNiches}>Import niches</button> : null}
          </div>
          <form className="job-form" onSubmit={createJob}>
            <label>Niche<select value={selectedNiche} onChange={(e) => setSelectedNiche(e.target.value)} required>
              <option value="">Select a niche</option>
              {niches.map((niche) => <option key={niche.id} value={niche.id}>{niche.title}{niche.needs_review ? " (review)" : ""}</option>)}
            </select></label>
            <label>Title<input value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} placeholder="Optional custom title" /></label>
            <label>Platform<select value={platform} onChange={(e) => setPlatform(e.target.value)}>
              <option>multi-platform</option>
              <option>facebook-instagram</option>
              <option>tiktok-youtube-shorts</option>
            </select></label>
            <label>Language<input value={language} onChange={(e) => setLanguage(e.target.value)} /></label>
            <button disabled={!can("jobs.create")}>Create job</button>
          </form>
        </article>

        <article className="panel">
          <h2>RBAC</h2>
          <p>{me?.user.email}</p>
          <p className="muted">{membership?.role.permissions.join(", ")}</p>
        </article>
      </section>

      <section className="panel">
        <h2>Jobs</h2>
        <div className="table">
          {jobs.map((job) => (
            <div className="row" key={job.id}>
              <div>
                <strong>{job.title}</strong>
                <p>{job.status} / {job.current_step} / {job.language}</p>
              </div>
              <div className="row-actions">
                <button disabled={!can("jobs.create")} onClick={() => jobAction(job, "advance")}>Advance</button>
                <button disabled={!can("jobs.approve")} onClick={() => jobAction(job, "approve")}>Approve</button>
                <button disabled={!can("jobs.render")} onClick={() => jobAction(job, "render")}>Render</button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {can("users.manage") ? (
        <section className="grid">
          <article className="panel">
            <h2>Create user</h2>
            <form className="form-stack" onSubmit={createUser}>
              <label>Email<input value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} /></label>
              <label>Name<input value={newUser.name} onChange={(e) => setNewUser({ ...newUser, name: e.target.value })} /></label>
              <label>Password<input type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} /></label>
              <label>Role<select value={newUser.role_id} onChange={(e) => setNewUser({ ...newUser, role_id: e.target.value })}>
                {roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}
              </select></label>
              <button>Create user</button>
            </form>
          </article>
          <article className="panel">
            <h2>Users</h2>
            <div className="table compact">
              {users.map((user) => <div className="row" key={user.id}><strong>{user.email}</strong><span>{user.is_active ? "active" : "disabled"}</span></div>)}
            </div>
          </article>
        </section>
      ) : null}
    </main>
  )
}

function App() {
  const { token, setToken, clear } = useLocalToken()
  if (!token) return <Login onLogin={setToken} />
  return <Dashboard token={token} clear={clear} />
}

createRoot(document.getElementById("root")!).render(<App />)
