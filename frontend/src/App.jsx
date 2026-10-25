
import { useEffect, useState } from "react";
import {
  ShieldCheck,
  LockKeyhole,
  UserRound,
  LogOut,
  LoaderCircle,
  Server,
  RefreshCw,
  CircleCheck,
  CircleX,
  LayoutDashboard,
  Users,
  ClipboardList,
  Menu,
  X,
  Plus,
  KeyRound,
  Copy,
  Ban,
  Activity,
  AlertCircle,
  Check,
  ChevronRight,
  MessageCircle,
  Send,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./App.css";

const API_URL = "";

const navigation = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "chat", label: "AI Assistant", icon: MessageCircle },
  { id: "servers", label: "MCP Servers", icon: Server },
  { id: "users", label: "Users & API Keys", icon: Users },
  { id: "audit", label: "Audit Logs", icon: ClipboardList },
];

const sectionInfo = {
  overview: {
    title: "Overview",
    description: "Monitor your MCP gateway and system health.",
  },
  chat: {
    title: "AI Assistant",
    description:
      "Ask questions about products, orders, currencies, and calculations.",
  },
  servers: {
    title: "MCP Servers",
    description: "Monitor the connectivity of your MCP services.",
  },
  users: {
    title: "Users & API Keys",
    description: "Manage accounts, roles, and access credentials.",
  },
  audit: {
    title: "Audit Logs",
    description: "Review recorded activity across your gateway.",
  },
};

// Normalize escaped Markdown returned by the AI.
// This allows escaped table pipes such as \| to be parsed as Markdown tables.
function normalizeMarkdown(content) {
  if (typeof content !== "string") return "";

  return content
    .replace(/\\+\|/g, "|")
    .replace(/\\([*_`#[\]()])/g, "$1");
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (response.status === 401) {
    throw new Error("Your session has expired. Please sign in again.");
  }

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status}).`
    );
  }

  return data;
}

// Reusable Markdown renderer for assistant messages.
function AssistantMarkdown({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        table: ({ children }) => (
          <div className="markdown-table-wrap">
            <table>{children}</table>
          </div>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
      }}
    >
      {normalizeMarkdown(content)}
    </ReactMarkdown>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [activePage, setActivePage] = useState("overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [servers, setServers] = useState([]);
  const [serversLoading, setServersLoading] = useState(false);
  const [serversError, setServersError] = useState("");

  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState("");
  const [userFormOpen, setUserFormOpen] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("member");
  const [creatingUser, setCreatingUser] = useState(false);

  const [selectedUser, setSelectedUser] = useState(null);
  const [keys, setKeys] = useState([]);
  const [keysLoading, setKeysLoading] = useState(false);
  const [keyName, setKeyName] = useState("default");
  const [newKey, setNewKey] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [keyMessage, setKeyMessage] = useState("");

  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState("");

  const [notice, setNotice] = useState("");
  const [actionError, setActionError] = useState("");

  const [chatMessages, setChatMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I'm your AI assistant. Ask me about WooCommerce products, orders, currency conversion, or calculations.",
    },
  ]);

  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/me`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) return null;
        const data = await response.json();
        return data.user;
      })
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    loadServers();
  }, [user]);

  useEffect(() => {
    if (!user) return;

    if (activePage === "users" && user.role === "admin") {
      loadUsers();
    }

    if (activePage === "audit") {
      loadAuditLogs();
    }
  }, [activePage, user]);

  async function loadServers() {
    setServersLoading(true);
    setServersError("");

    try {
      const data = await apiRequest("/api/servers");
      setServers(data.servers || []);
    } catch (err) {
      setServersError(err.message);
      if (err.message.includes("session has expired")) setUser(null);
    } finally {
      setServersLoading(false);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed.");
      }

      setUser(data.user);
      setPassword("");
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot reach the dashboard API. Check that port 8005 is running."
          : err.message
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout() {
    try {
      await fetch(`${API_URL}/api/logout`, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      setUser(null);
      setPassword("");
      setServers([]);
      setUsers([]);
      setLogs([]);
      setSelectedUser(null);
      setKeys([]);
      setNewKey("");

      setChatMessages([
        {
          role: "assistant",
          content: "Hi! I'm your AI assistant. How can I help?",
        },
      ]);

      setChatInput("");
      setChatError("");
      setActivePage("overview");
    }
  }

  async function loadUsers() {
    setUsersLoading(true);
    setUsersError("");

    try {
      const data = await apiRequest("/api/users");
      setUsers(Array.isArray(data) ? data : data.users || []);
    } catch (err) {
      setUsersError(err.message);
      if (err.message.includes("session has expired")) setUser(null);
    } finally {
      setUsersLoading(false);
    }
  }

  async function createUser(event) {
    event.preventDefault();
    setCreatingUser(true);
    setUsersError("");
    setActionError("");
    setNotice("");

    try {
      await apiRequest("/api/users", {
        method: "POST",
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword,
          role: newRole,
        }),
      });

      setNotice("User created successfully.");
      setNewUsername("");
      setNewPassword("");
      setNewRole("member");
      setUserFormOpen(false);
      await loadUsers();
    } catch (err) {
      setActionError(err.message);
      if (err.message.includes("session has expired")) setUser(null);
    } finally {
      setCreatingUser(false);
    }
  }

  async function loadKeys(targetUser) {
    setSelectedUser(targetUser);
    setKeys([]);
    setActionError("");
    setKeyMessage("");
    setNewKey("");
    setKeysLoading(true);

    try {
      const data = await apiRequest(`/api/users/${targetUser.id}/keys`);
      setKeys(Array.isArray(data) ? data : data.keys || []);
    } catch (err) {
      setActionError(err.message);
      if (err.message.includes("session has expired")) setUser(null);
    } finally {
      setKeysLoading(false);
    }
  }

  async function createKey(event) {
    event.preventDefault();

    if (!selectedUser || creatingKey) return;

    setCreatingKey(true);
    setActionError("");
    setKeyMessage("");
    setNewKey("");

    try {
      const data = await apiRequest(`/api/users/${selectedUser.id}/keys`, {
        method: "POST",
        body: JSON.stringify({ name: keyName.trim() || "default" }),
      });

      const plaintext = data.api_key || data.key || data.token;

      if (plaintext) {
        setNewKey(plaintext);
        setKeyMessage("Copy this key now. It will not be shown again.");
      } else {
        setKeyMessage(
          "The server returned no key secret. Check the API response."
        );
      }

      setKeyName("default");
      setKeysLoading(true);

      try {
        const refreshed = await apiRequest(
          `/api/users/${selectedUser.id}/keys`
        );

        setKeys(
          Array.isArray(refreshed) ? refreshed : refreshed.keys || []
        );
      } catch (refreshError) {
        setActionError(
          `Key creation may have succeeded, but refreshing the list failed: ${refreshError.message}`
        );
      } finally {
        setKeysLoading(false);
      }
    } catch (err) {
      setActionError(err.message);
      if (err.message.includes("session has expired")) setUser(null);
    } finally {
      setCreatingKey(false);
    }
  }

  async function copyKey() {
    try {
      await navigator.clipboard.writeText(newKey);
      setKeyMessage("API key copied to clipboard.");
    } catch {
      setKeyMessage(
        "Copy failed. Select the displayed key and copy it manually."
      );
    }
  }

  async function revokeKey(key) {
    if (!window.confirm("Revoke this API key? This action cannot be undone.")) {
      return;
    }

    setActionError("");
    setKeyMessage("");

    try {
      await apiRequest(`/api/keys/${key.id}/revoke`, {
        method: "POST",
      });

      setKeyMessage("API key revoked.");

      if (selectedUser) {
        const data = await apiRequest(
          `/api/users/${selectedUser.id}/keys`
        );

        setKeys(Array.isArray(data) ? data : data.keys || []);
      }
    } catch (err) {
      setActionError(err.message);
      if (err.message.includes("session has expired")) setUser(null);
    }
  }

  async function loadAuditLogs() {
    setLogsLoading(true);
    setLogsError("");

    try {
      const data = await apiRequest("/api/audit-logs");
      setLogs(Array.isArray(data) ? data : data.logs || []);
    } catch (err) {
      setLogsError(err.message);
      if (err.message.includes("session has expired")) setUser(null);
    } finally {
      setLogsLoading(false);
    }
  }

  async function sendChatMessage(event) {
    event.preventDefault();

    const message = chatInput.trim();
    if (!message || chatLoading) return;

    setChatMessages((previous) => [
      ...previous,
      { role: "user", content: message },
    ]);

    setChatInput("");
    setChatError("");
    setChatLoading(true);

    try {
      const data = await apiRequest("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message }),
      });

      setChatMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer || "No response received.",
        },
      ]);
    } catch (err) {
      setChatError(err.message);

      if (err.message.includes("session has expired")) {
        setUser(null);
      }
    } finally {
      setChatLoading(false);
    }
  }

  function navigate(page) {
    setActivePage(page);
    setSidebarOpen(false);
    setNotice("");
    setActionError("");
    setChatError("");
  }

  if (loading) {
    return (
      <div className="login-loading">
        <LoaderCircle className="spin" /> Loading dashboard...
      </div>
    );
  }

  if (!user) {
    return (
      <main className="login-page">
        <section className="login-card">
          <div className="login-logo">
            <ShieldCheck size={29} />
          </div>

          <p className="login-eyebrow">MCP MANAGEMENT PLATFORM</p>
          <h1>Welcome back</h1>
          <p className="login-subtitle">
            Sign in to your gateway dashboard.
          </p>

          <form onSubmit={handleLogin}>
            <label htmlFor="username">Username</label>

            <div className="login-input-wrap">
              <UserRound size={18} />
              <input
                id="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter your username"
                required
              />
            </div>

            <label htmlFor="password">Password</label>

            <div className="login-input-wrap">
              <LockKeyhole size={18} />
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                required
              />
            </div>

            {error && (
              <p className="login-error" role="alert">
                {error}
              </p>
            )}

            <button className="login-submit" disabled={submitting}>
              {submitting ? (
                <LoaderCircle className="spin" size={18} />
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <p className="login-security">
            <LockKeyhole size={14} /> Secure, role-based access
          </p>
        </section>

        <p className="login-footer">MCP Gateway Â· Local development</p>
      </main>
    );
  }

  const onlineCount = servers.filter(
    (server) => server.status === "online"
  ).length;

  const isAdmin = user.role === "admin";
  const pageInfo = sectionInfo[activePage] || sectionInfo.overview;

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`app-sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <ShieldCheck size={24} />
          </div>

          <div>
            <strong>MCP Gateway</strong>
            <span>Management Console</span>
          </div>

          <button
            className="sidebar-close"
            aria-label="Close menu"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={19} />
          </button>
        </div>

        <p className="sidebar-label">WORKSPACE</p>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigation.map((item) => {
            const Icon = item.icon;
            const disabled = item.id === "users" && !isAdmin;

            return (
              <button
                key={item.id}
                className={`nav-item ${
                  activePage === item.id ? "active" : ""
                }`}
                onClick={() => !disabled && navigate(item.id)}
                disabled={disabled}
                title={disabled ? "Admin access required" : item.label}
              >
                <Icon size={19} />
                <span>{item.label}</span>
                {activePage === item.id && <ChevronRight size={16} />}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-security">
            <LockKeyhole size={17} />
            <div>
              <strong>Secure gateway</strong>
              <span>Role-based access enabled</span>
            </div>
          </div>

          <div className="sidebar-user">
            <div className="user-avatar">
              {user.username?.charAt(0).toUpperCase()}
            </div>

            <div className="sidebar-user-info">
              <strong>{user.username}</strong>
              <span>{user.role}</span>
            </div>

            <button
              className="icon-button"
              onClick={handleLogout}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      <main className="app-main">
        <header className="topbar">
          <button
            className="mobile-menu-button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={21} />
          </button>

          <div className="breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={15} />
            <strong>{pageInfo.title}</strong>
          </div>

          <div className="topbar-right">
            <span className="topbar-status">
              <span /> Local environment
            </span>

            <div className="topbar-avatar">
              {user.username?.charAt(0).toUpperCase()}
            </div>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <p className="login-eyebrow">MCP MANAGEMENT PLATFORM</p>
              <h1>{pageInfo.title}</h1>
              <p>{pageInfo.description}</p>
            </div>

            {activePage === "servers" && (
              <button
                className="primary-action"
                onClick={loadServers}
                disabled={serversLoading}
              >
                <RefreshCw
                  size={16}
                  className={serversLoading ? "spin" : ""}
                />
                Refresh status
              </button>
            )}

            {activePage === "users" && isAdmin && (
              <button
                className="primary-action"
                onClick={() => {
                  setUserFormOpen(!userFormOpen);
                  setActionError("");
                  setNotice("");
                }}
              >
                <Plus size={17} /> Add user
              </button>
            )}

            {activePage === "audit" && (
              <button
                className="primary-action"
                onClick={loadAuditLogs}
                disabled={logsLoading}
              >
                <RefreshCw
                  size={16}
                  className={logsLoading ? "spin" : ""}
                />
                Refresh logs
              </button>
            )}
          </div>

          {notice && (
            <div className="notice-message">
              <Check size={17} /> {notice}
            </div>
          )}

          {actionError && (
            <div className="error-message">
              <AlertCircle size={17} /> {actionError}
            </div>
          )}

          {/* OVERVIEW */}
          {activePage === "overview" && (
            <>
              <section className="overview-hero">
                <div>
                  <div className="hero-tag">
                    <Activity size={15} /> SYSTEM OVERVIEW
                  </div>
                  <h2>Welcome back, {user.username}</h2>
                  <p>Your MCP gateway control center is ready.</p>
                </div>

                <div className="hero-mark">
                  <ShieldCheck size={55} />
                </div>
              </section>

              <section className="stats-grid">
                <article className="stat-card">
                  <div className="stat-top">
                    <span>Signed-in user</span>
                    <div className="stat-icon blue">
                      <UserRound size={19} />
                    </div>
                  </div>
                  <strong className="stat-value stat-text">
                    {user.username}
                  </strong>
                  <span className="stat-foot">Authenticated account</span>
                </article>

                <article className="stat-card">
                  <div className="stat-top">
                    <span>Account role</span>
                    <div className="stat-icon violet">
                      <ShieldCheck size={19} />
                    </div>
                  </div>
                  <strong className="stat-value">{user.role}</strong>
                  <span className="stat-foot">
                    Role-based permissions
                  </span>
                </article>

                <article className="stat-card">
                  <div className="stat-top">
                    <span>Services online</span>
                    <div className="stat-icon green">
                      <Server size={19} />
                    </div>
                  </div>
                  <strong className="stat-value">
                    {serversLoading
                      ? "â€¦"
                      : `${onlineCount} / ${servers.length || 4}`}
                  </strong>
                  <span className="stat-foot">
                    Live port connectivity checks
                  </span>
                </article>

                <article className="stat-card">
                  <div className="stat-top">
                    <span>Services monitored</span>
                    <div className="stat-icon amber">
                      <Activity size={19} />
                    </div>
                  </div>
                  <strong className="stat-value">
                    {servers.length || 4}
                  </strong>
                  <span className="stat-foot">
                    Registered MCP services
                  </span>
                </article>
              </section>

              <section className="content-panel">
                <div className="panel-heading">
                  <div>
                    <h2>
                      <Server size={20} /> MCP service health
                    </h2>
                    <p>Current status from the dashboard API</p>
                  </div>

                  <button
                    className="text-action"
                    onClick={() => navigate("servers")}
                  >
                    View all <ChevronRight size={16} />
                  </button>
                </div>

                {serversError && (
                  <p className="login-error">{serversError}</p>
                )}

                {serversLoading && servers.length === 0 && (
                  <p className="empty-state">Checking MCP servicesâ€¦</p>
                )}

                {!serversLoading &&
                  servers.length === 0 &&
                  !serversError && (
                    <p className="empty-state">
                      No service status is available yet.
                    </p>
                  )}

                <div className="overview-server-list">
                  {servers.map((server) => (
                    <div
                      className="overview-server-row"
                      key={server.port}
                    >
                      <div className="mini-server-icon">
                        <Server size={18} />
                      </div>

                      <div className="overview-server-name">
                        <strong>{server.name}</strong>
                        <span>Port {server.port}</span>
                      </div>

                      <span className={`status-pill ${server.status}`}>
                        {server.status === "online" ? (
                          <CircleCheck size={15} />
                        ) : (
                          <CircleX size={15} />
                        )}
                        {server.status}
                      </span>
                    </div>
                  ))}
                </div>

                <p className="panel-footnote">
                  Status reflects local port connectivity, not a full MCP
                  tool test.
                </p>
              </section>

              <section className="content-panel quick-actions-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Quick navigation</h2>
                    <p>Jump to a management area</p>
                  </div>
                </div>

                <div className="quick-actions-grid">
                  <button onClick={() => navigate("servers")}>
                    <Server size={21} />
                    <span>
                      <strong>MCP Servers</strong>
                      <small>Check service health</small>
                    </span>
                    <ChevronRight size={17} />
                  </button>

                  <button onClick={() => navigate("chat")}>
                    <MessageCircle size={21} />
                    <span>
                      <strong>AI Assistant</strong>
                      <small>Ask questions and use MCP tools</small>
                    </span>
                    <ChevronRight size={17} />
                  </button>

                  {isAdmin && (
                    <button onClick={() => navigate("users")}>
                      <Users size={21} />
                      <span>
                        <strong>Users & API Keys</strong>
                        <small>Manage gateway access</small>
                      </span>
                      <ChevronRight size={17} />
                    </button>
                  )}

                  <button onClick={() => navigate("audit")}>
                    <ClipboardList size={21} />
                    <span>
                      <strong>Audit Logs</strong>
                      <small>Review tool activity</small>
                    </span>
                    <ChevronRight size={17} />
                  </button>
                </div>
              </section>
            </>
          )}

          {/* AI ASSISTANT */}
          {activePage === "chat" && (
            <section className="content-panel chat-panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    <MessageCircle size={20} /> AI Shopping Assistant
                  </h2>
                  <p>
                    Ask about WooCommerce products, orders, currency
                    conversion, and calculations.
                  </p>
                </div>
              </div>

              <div className="chat-messages" aria-live="polite">
                {chatMessages.map((message, index) => (
                  <div
                    key={index}
                    className={`chat-message ${
                      message.role === "user"
                        ? "chat-user"
                        : "chat-assistant"
                    }`}
                  >
                    <span className="chat-role">
                      {message.role === "user" ? "You" : "AI Assistant"}
                    </span>

                    <div className="chat-message-content">
                      {message.role === "assistant" ? (
                        <AssistantMarkdown content={message.content} />
                      ) : (
                        <p>{message.content}</p>
                      )}
                    </div>
                  </div>
                ))}

                {chatLoading && (
                  <div className="chat-message chat-assistant">
                    <span className="chat-role">AI Assistant</span>
                    <p className="chat-thinking">
                      <LoaderCircle size={16} className="spin" />
                      Thinking and checking available tools...
                    </p>
                  </div>
                )}
              </div>

              {chatError && (
                <div className="error-message" role="alert">
                  <AlertCircle size={17} />
                  {chatError}
                </div>
              )}

              <form className="chat-form" onSubmit={sendChatMessage}>
                <input
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="Ask about products, orders, or calculations..."
                  aria-label="Your message"
                  maxLength={2000}
                  disabled={chatLoading}
                  required
                />

                <button
                  type="submit"
                  className="primary-action"
                  disabled={chatLoading || !chatInput.trim()}
                >
                  {chatLoading ? (
                    <LoaderCircle size={17} className="spin" />
                  ) : (
                    <Send size={17} />
                  )}
                  Send
                </button>
              </form>

              <div className="chat-suggestions">
                <span>Try asking:</span>

                <button
                  type="button"
                  onClick={() =>
                    setChatInput("Show me the first 5 products in my store.")
                  }
                  disabled={chatLoading}
                >
                  Show my products
                </button>

                <button
                  type="button"
                  onClick={() => setChatInput("Convert 100 USD to INR.")}
                  disabled={chatLoading}
                >
                  Convert currency
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setChatInput("Calculate 250 multiplied by 4.")
                  }
                  disabled={chatLoading}
                >
                  Calculate
                </button>
              </div>

              <p className="panel-footnote">
                The AI uses backend tools when needed. Answers depend on
                available data, permissions, and tool results.
              </p>
            </section>
          )}

          {/* MCP SERVERS */}
          {activePage === "servers" && (
            <section className="content-panel">
              <div className="panel-heading">
                <div>
                  <h2>Server registry</h2>
                  <p>
                    {onlineCount} of {servers.length || 4} services
                    currently online
                  </p>
                </div>

                <span className="live-indicator">
                  <span /> Live status
                </span>
              </div>

              {serversError && (
                <div className="error-message">
                  <AlertCircle size={17} /> {serversError}
                </div>
              )}

              {serversLoading && servers.length === 0 && (
                <p className="empty-state">Checking MCP servicesâ€¦</p>
              )}

              <div className="server-registry-grid">
                {servers.map((server) => (
                  <article
                    className="registry-card"
                    key={server.port}
                  >
                    <div className="registry-card-top">
                      <div className="registry-icon">
                        <Server size={22} />
                      </div>

                      <span className={`status-pill ${server.status}`}>
                        {server.status === "online" ? (
                          <CircleCheck size={15} />
                        ) : (
                          <CircleX size={15} />
                        )}
                        {server.status}
                      </span>
                    </div>

                    <h3>{server.name}</h3>
                    <p>Local service endpoint</p>

                    <div className="registry-port">
                      <span>PORT</span>
                      <strong>{server.port}</strong>
                    </div>
                  </article>
                ))}
              </div>

              {!serversLoading &&
                servers.length === 0 &&
                !serversError && (
                  <p className="empty-state">
                    No server records returned by the API.
                  </p>
                )}

              <p className="panel-footnote">
                A reachable port does not guarantee that every MCP tool
                is working.
              </p>
            </section>
          )}

          {/* USERS AND API KEYS */}
          {activePage === "users" &&
            (isAdmin ? (
              <>
                {userFormOpen && (
                  <section className="content-panel form-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Create a user</h2>
                        <p>
                          New passwords must contain at least 12
                          characters.
                        </p>
                      </div>

                      <button
                        className="icon-button"
                        onClick={() => setUserFormOpen(false)}
                        aria-label="Close form"
                      >
                        <X size={19} />
                      </button>
                    </div>

                    <form
                      className="management-form"
                      onSubmit={createUser}
                    >
                      <label>
                        Username
                        <input
                          value={newUsername}
                          onChange={(event) =>
                            setNewUsername(event.target.value)
                          }
                          minLength={1}
                          maxLength={100}
                          autoComplete="off"
                          required
                          placeholder="Enter a username"
                        />
                      </label>

                      <label>
                        Password
                        <input
                          type="password"
                          value={newPassword}
                          onChange={(event) =>
                            setNewPassword(event.target.value)
                          }
                          minLength={12}
                          maxLength={200}
                          autoComplete="new-password"
                          required
                          placeholder="At least 12 characters"
                        />
                      </label>

                      <label>
                        Role
                        <select
                          value={newRole}
                          onChange={(event) =>
                            setNewRole(event.target.value)
                          }
                        >
                          <option value="member">Member</option>
                          <option value="admin">Admin</option>
                        </select>
                      </label>

                      <button
                        className="primary-action"
                        disabled={creatingUser}
                      >
                        {creatingUser && (
                          <LoaderCircle size={17} className="spin" />
                        )}
                        Create user
                      </button>
                    </form>
                  </section>
                )}

                <section className="content-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Platform users</h2>
                      <p>Account information and API-key access</p>
                    </div>

                    <button
                      className="secondary-action"
                      onClick={loadUsers}
                      disabled={usersLoading}
                    >
                      <RefreshCw
                        size={15}
                        className={usersLoading ? "spin" : ""}
                      />
                      Refresh
                    </button>
                  </div>

                  {usersError && (
                    <div className="error-message">
                      <AlertCircle size={17} /> {usersError}
                    </div>
                  )}

                  {usersLoading && (
                    <p className="empty-state">Loading usersâ€¦</p>
                  )}

                  {!usersLoading &&
                    users.length === 0 &&
                    !usersError && (
                      <p className="empty-state">
                        No users returned by the API.
                      </p>
                    )}

                  {users.length > 0 && (
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>User</th>
                            <th>Role</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Access</th>
                          </tr>
                        </thead>

                        <tbody>
                          {users.map((item) => (
                            <tr key={item.id}>
                              <td>
                                <div className="table-user">
                                  <div className="user-avatar small">
                                    {item.username
                                      ?.charAt(0)
                                      .toUpperCase()}
                                  </div>
                                  <strong>{item.username}</strong>
                                </div>
                              </td>

                              <td>
                                <span className={`role-badge ${item.role}`}>
                                  {item.role}
                                </span>
                              </td>

                              <td>
                                <span
                                  className={`account-status ${
                                    item.is_active === false
                                      ? "inactive"
                                      : "active"
                                  }`}
                                >
                                  {item.is_active === false
                                    ? "Inactive"
                                    : "Active"}
                                </span>
                              </td>

                              <td>
                                {item.created_at
                                  ? new Date(
                                      item.created_at
                                    ).toLocaleDateString()
                                  : "â€”"}
                              </td>

                              <td>
                                <button
                                  className="table-action"
                                  onClick={() => loadKeys(item)}
                                >
                                  <KeyRound size={15} /> API keys
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>

                {selectedUser && (
                  <section className="content-panel keys-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>
                          <KeyRound size={20} /> API keys
                        </h2>
                        <p>
                          Keys belonging to {selectedUser.username}
                        </p>
                      </div>

                      <button
                        className="icon-button"
                        onClick={() => {
                          setSelectedUser(null);
                          setKeys([]);
                          setNewKey("");
                          setKeyMessage("");
                          setActionError("");
                        }}
                        aria-label="Close API keys"
                      >
                        <X size={19} />
                      </button>
                    </div>

                    <form
                      className="inline-key-form"
                      onSubmit={createKey}
                    >
                      <label>
                        Key name
                        <input
                          value={keyName}
                          onChange={(event) =>
                            setKeyName(event.target.value)
                          }
                          maxLength={100}
                          required
                          placeholder="e.g. local-development"
                        />
                      </label>

                      <button
                        className="primary-action"
                        disabled={creatingKey}
                      >
                        {creatingKey ? (
                          <LoaderCircle
                            size={16}
                            className="spin"
                          />
                        ) : (
                          <Plus size={16} />
                        )}
                        Generate API key
                      </button>
                    </form>

                    {newKey && (
                      <div className="key-secret-box">
                        <div>
                          <strong>
                            <ShieldCheck size={17} /> Newly generated API key
                          </strong>
                          <p>
                            Copy and store this secret now. It cannot
                            be retrieved later.
                          </p>
                        </div>

                        <code>{newKey}</code>

                        <button
                          className="secondary-action"
                          onClick={copyKey}
                          type="button"
                        >
                          <Copy size={15} /> Copy key
                        </button>
                      </div>
                    )}

                    {keyMessage && (
                      <div className="notice-message">
                        <Check size={17} /> {keyMessage}
                      </div>
                    )}

                    {keysLoading && (
                      <p className="empty-state">Loading API keysâ€¦</p>
                    )}

                    {!keysLoading && keys.length === 0 && (
                      <p className="empty-state">
                        No API keys found for this user yet.
                      </p>
                    )}

                    {keys.length > 0 && (
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Name</th>
                              <th>Status</th>
                              <th>Created</th>
                              <th>Action</th>
                            </tr>
                          </thead>

                          <tbody>
                            {keys.map((key) => (
                              <tr key={key.id}>
                                <td>
                                  <strong>
                                    {key.name || "Unnamed key"}
                                  </strong>
                                </td>

                                <td>
                                  <span
                                    className={`account-status ${
                                      key.revoked
                                        ? "inactive"
                                        : "active"
                                    }`}
                                  >
                                    {key.revoked ? "Revoked" : "Active"}
                                  </span>
                                </td>

                                <td>
                                  {key.created_at
                                    ? new Date(
                                        key.created_at
                                      ).toLocaleDateString()
                                    : "â€”"}
                                </td>

                                <td>
                                  {!key.revoked && (
                                    <button
                                      className="table-action danger-action"
                                      onClick={() => revokeKey(key)}
                                      type="button"
                                    >
                                      <Ban size={15} /> Revoke
                                    </button>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    <p className="panel-footnote">
                      Existing key secrets are never displayed; only a
                      newly generated key is shown once.
                    </p>
                  </section>
                )}
              </>
            ) : (
              <section className="content-panel">
                <p className="empty-state">
                  Admin access is required to manage users and API keys.
                </p>
              </section>
            ))}

          {/* AUDIT LOGS */}
          {activePage === "audit" && (
            <section className="content-panel">
              <div className="panel-heading">
                <div>
                  <h2>Activity history</h2>
                  <p>
                    Recorded gateway tool calls and their outcomes
                  </p>
                </div>

                <span className="count-badge">
                  {logs.length} records
                </span>
              </div>

              {logsError && (
                <div className="error-message">
                  <AlertCircle size={17} />
                  {logsError}
                  <span className="audit-hint">
                    The audit endpoint must be available in the dashboard API.
                  </span>
                </div>
              )}

              {logsLoading && (
                <p className="empty-state">Loading audit logsâ€¦</p>
              )}

              {!logsLoading && !logsError && logs.length === 0 && (
                <p className="empty-state">No audit records found.</p>
              )}

              {logs.length > 0 && (
                <div className="table-wrap">
                  <table className="data-table audit-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>User</th>
                        <th>MCP server</th>
                        <th>Tool</th>
                        <th>Duration</th>
                        <th>Outcome</th>
                        <th>Details</th>
                      </tr>
                    </thead>

                    <tbody>
                      {logs.map((log, index) => (
                        <tr key={log.id ?? `${log.timestamp}-${index}`}>
                          <td>
                            {log.timestamp
                              ? new Date(
                                  log.timestamp
                                ).toLocaleString()
                              : "â€”"}
                          </td>

                          <td>{log.username || log.user_id || "â€”"}</td>
                          <td>{log.upstream_server || "â€”"}</td>
                          <td>
                            <code>{log.tool_name || "â€”"}</code>
                          </td>
                          <td>
                            {log.duration_ms != null
                              ? `${log.duration_ms} ms`
                              : "â€”"}
                          </td>
                          <td>
                            <span
                              className={`account-status ${
                                String(log.outcome).toLowerCase() === "success"
                                  ? "active"
                                  : "inactive"
                              }`}
                            >
                              {log.outcome || "â€”"}
                            </span>
                          </td>
                          <td>{log.details || "â€”"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <p className="panel-footnote">
                Audit history should be served from the gateway's
                persisted audit records.
              </p>
            </section>
          )}

          <footer className="app-footer">
            <span>
              <ShieldCheck size={15} /> MCP Gateway Management Console
            </span>
            <span>Local development environment</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
