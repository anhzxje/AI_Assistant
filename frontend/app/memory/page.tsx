"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, Plus, Trash2 } from "lucide-react";
import {
  MemoryRecord,
  MemorySummary,
  TaskRecord,
  createTask,
  deleteMemory,
  deleteTask,
  fetchMemorySummary,
  rememberFact,
  updateTask
} from "@/lib/api";
import { useAuthSession } from "@/lib/auth";
import { loadActiveConversationId, sessionStorageKey } from "@/lib/storage";

export default function MemoryPage() {
  const { session, ready } = useAuthSession();
  const userId = session?.user.user_id ?? "guest";
  const [summary, setSummary] = useState<MemorySummary | null>(null);
  const [memoryText, setMemoryText] = useState("");
  const [memoryType, setMemoryType] = useState("fact");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskPriority, setTaskPriority] = useState("medium");
  const [taskDueDate, setTaskDueDate] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [sessionId, setSessionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    const activeConversationId = loadActiveConversationId(userId);
    const existing = activeConversationId
      ? window.localStorage.getItem(sessionStorageKey(userId, activeConversationId)) ?? activeConversationId
      : "";
    setSessionId(existing);
    load(existing);
  }, [ready, userId]);

  async function load(activeSessionId = sessionId) {
    setLoading(true);
    setError(null);
    try {
      setSummary(await fetchMemorySummary({ userId, sessionId: activeSessionId || undefined }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function onRemember(event: FormEvent) {
    event.preventDefault();
    if (!memoryText.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await rememberFact({
        text: memoryText.trim(),
        userId,
        sessionId: sessionId || undefined,
        memoryType
      });
      setMemoryText("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  async function onCreateTask(event: FormEvent) {
    event.preventDefault();
    if (!taskTitle.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createTask({
        title: taskTitle.trim(),
        userId,
        priority: taskPriority,
        dueDate: taskDueDate || undefined
      });
      setTaskTitle("");
      setTaskDueDate("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  async function removeMemory(memory: MemoryRecord) {
    await deleteMemory(memory.memory_id, userId);
    await load();
  }

  async function markDone(task: TaskRecord) {
    await updateTask(task.task_id, { status: "done" }, userId);
    await load();
  }

  async function removeTask(task: TaskRecord) {
    await deleteTask(task.task_id, userId);
    await load();
  }

  const filteredTasks = useMemo(() => {
    const tasks = summary?.upcoming_tasks ?? [];
    return tasks.filter((task) => {
      const statusOk = statusFilter === "all" || task.status === statusFilter;
      const priorityOk = priorityFilter === "all" || task.priority === priorityFilter;
      return statusOk && priorityOk;
    });
  }, [summary, statusFilter, priorityFilter]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Personal Memory</h1>
          <p className="mt-1 text-sm text-slate-500">
            Explicit remembered facts and task memory for <span className="font-medium">{session?.user.email ?? userId}</span>.
          </p>
        </div>
        <button
          onClick={() => load()}
          className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Refresh
        </button>
      </div>

      {error ? (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-4">
        <Metric label="Memories" value={summary?.long_term_memories_count ?? 0} />
        <Metric label="Tasks" value={summary?.tasks_count ?? 0} />
        <Metric label="Session turns" value={summary?.recent_session_count ?? 0} />
        <Metric label="Storage" value={summary?.storage_mode.long_term ?? "loading"} />
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <form onSubmit={onRemember} className="rounded-lg border border-line bg-white p-5">
          <h2 className="text-base font-semibold text-ink">Add remembered fact</h2>
          <div className="mt-4 grid gap-3">
            <textarea
              value={memoryText}
              onChange={(event) => setMemoryText(event.target.value)}
              rows={4}
              className="focus-ring resize-none rounded-md border border-line px-3 py-2 text-sm"
              placeholder="Example: Remember that I prefer concise answers."
            />
            <div className="flex gap-3">
              <select
                value={memoryType}
                onChange={(event) => setMemoryType(event.target.value)}
                className="rounded-md border border-line bg-white px-3 py-2 text-sm"
              >
                <option value="fact">Fact</option>
                <option value="preference">Preference</option>
                <option value="profile">Profile</option>
                <option value="recurring_task">Recurring task</option>
              </select>
              <button
                disabled={saving || !memoryText.trim()}
                className="focus-ring inline-flex items-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Remember
              </button>
            </div>
          </div>
        </form>

        <form onSubmit={onCreateTask} className="rounded-lg border border-line bg-white p-5">
          <h2 className="text-base font-semibold text-ink">Create task</h2>
          <div className="mt-4 grid gap-3">
            <input
              value={taskTitle}
              onChange={(event) => setTaskTitle(event.target.value)}
              className="focus-ring rounded-md border border-line px-3 py-2 text-sm"
              placeholder="Task title"
            />
            <div className="grid gap-3 sm:grid-cols-3">
              <input
                type="date"
                value={taskDueDate}
                onChange={(event) => setTaskDueDate(event.target.value)}
                className="rounded-md border border-line px-3 py-2 text-sm"
              />
              <select
                value={taskPriority}
                onChange={(event) => setTaskPriority(event.target.value)}
                className="rounded-md border border-line bg-white px-3 py-2 text-sm"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
              <button
                disabled={saving || !taskTitle.trim()}
                className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
              >
                <Plus className="h-4 w-4" />
                Add
              </button>
            </div>
          </div>
        </form>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-lg border border-line bg-white">
          <div className="border-b border-line px-5 py-4">
            <h2 className="text-base font-semibold text-ink">Remembered facts</h2>
          </div>
          <div className="divide-y divide-line">
            {loading ? <Empty text="Loading memories..." /> : null}
            {!loading && (summary?.recent_memories.length ?? 0) === 0 ? <Empty text="No memories yet." /> : null}
            {summary?.recent_memories.map((memory) => (
              <div key={memory.memory_id} className="flex items-start justify-between gap-3 p-4">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">{memory.memory_type}</div>
                  <p className="mt-1 text-sm leading-6 text-slate-800">{memory.content}</p>
                  <div className="mt-1 text-xs text-slate-500">importance {memory.importance.toFixed(2)}</div>
                </div>
                <button
                  onClick={() => removeMemory(memory)}
                  className="focus-ring rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-red-600"
                  title="Delete memory"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-white">
          <div className="border-b border-line px-5 py-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-ink">Tasks</h2>
              <div className="flex gap-2">
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  className="rounded-md border border-line bg-white px-2 py-1 text-xs"
                >
                  <option value="all">All status</option>
                  <option value="open">Open</option>
                  <option value="in_progress">In progress</option>
                  <option value="done">Done</option>
                  <option value="cancelled">Cancelled</option>
                </select>
                <select
                  value={priorityFilter}
                  onChange={(event) => setPriorityFilter(event.target.value)}
                  className="rounded-md border border-line bg-white px-2 py-1 text-xs"
                >
                  <option value="all">All priority</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>
          <div className="divide-y divide-line">
            {loading ? <Empty text="Loading tasks..." /> : null}
            {!loading && filteredTasks.length === 0 ? <Empty text="No tasks match the filters." /> : null}
            {filteredTasks.map((task) => (
              <div key={task.task_id} className="flex items-start justify-between gap-3 p-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded bg-slate-100 px-2 py-1 font-medium text-slate-700">{task.status}</span>
                    <span className="rounded bg-slate-100 px-2 py-1 font-medium text-slate-700">{task.priority}</span>
                    {task.due_date ? <span className="text-slate-500">due {task.due_date}</span> : null}
                  </div>
                  <p className="mt-2 text-sm font-medium text-slate-800">{task.title}</p>
                </div>
                <div className="flex gap-1">
                  {task.status !== "done" ? (
                    <button
                      onClick={() => markDone(task)}
                      className="focus-ring rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-green-700"
                      title="Mark done"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                    </button>
                  ) : null}
                  <button
                    onClick={() => removeTask(task)}
                    className="focus-ring rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-red-600"
                    title="Delete task"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 break-words text-xl font-semibold text-ink">{value}</div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="p-4 text-sm text-slate-500">{text}</div>;
}
