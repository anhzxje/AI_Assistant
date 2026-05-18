"use client";

import {
  Archive,
  Download,
  LogOut,
  Menu,
  MessageSquarePlus,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
  X
} from "lucide-react";
import { useMemo, useState } from "react";
import { AppLogo } from "@/components/brand/AppLogo";
import type { AuthUser } from "@/lib/api";
import { isMeaningfulConversation, type Conversation } from "@/lib/types";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function ConversationSidebar({
  conversations,
  activeConversationId,
  mobileOpen,
  user,
  onMobileOpenChange,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onArchive,
  onRestore,
  onExport,
  onLogout
}: {
  conversations: Conversation[];
  activeConversationId: string;
  mobileOpen: boolean;
  user: AuthUser | null;
  onMobileOpenChange: (open: boolean) => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string) => void;
  onDelete: (id: string) => void;
  onArchive: (id: string) => void;
  onRestore: (id: string) => void;
  onExport: (id: string) => void;
  onLogout: () => void;
}) {
  const [showArchived, setShowArchived] = useState(false);
  const visibleConversations = useMemo(
    () =>
      [...conversations]
        .filter(isMeaningfulConversation)
        .filter((conversation) => Boolean(conversation.archived) === showArchived)
        .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()),
    [conversations, showArchived]
  );

  const panel = (
    <aside className="flex h-full min-h-0 w-80 flex-col border-r border-line bg-white">
      <div className="border-b border-line p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <AppLogo compact />
          </div>
          <button
            type="button"
            onClick={() => onMobileOpenChange(false)}
            title="Close sidebar"
            className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="grid gap-2 p-3">
        <button
          type="button"
          onClick={onNew}
          className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md bg-brand px-3 text-sm font-medium text-white hover:bg-cyan-800"
        >
          <Plus className="h-4 w-4" />
          Chat mới
        </button>
      </div>

      <div className="flex items-center gap-1 border-y border-line px-3 py-2">
        <button
          type="button"
          onClick={() => setShowArchived(false)}
          className={`focus-ring flex-1 rounded-md px-3 py-1.5 text-xs font-medium ${
            !showArchived ? "bg-cyan-50 text-cyan-900" : "text-slate-500 hover:bg-slate-50"
          }`}
        >
          Gần đây
        </button>
        <button
          type="button"
          onClick={() => setShowArchived(true)}
          className={`focus-ring flex-1 rounded-md px-3 py-1.5 text-xs font-medium ${
            showArchived ? "bg-cyan-50 text-cyan-900" : "text-slate-500 hover:bg-slate-50"
          }`}
        >
          Đã lưu trữ
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {visibleConversations.length ? (
          <div className="flex flex-col gap-1">
            {visibleConversations.map((conversation) => (
              <ConversationRow
                key={conversation.id}
                active={conversation.id === activeConversationId}
                conversation={conversation}
                archived={showArchived}
                onSelect={(id) => {
                  onSelect(id);
                  onMobileOpenChange(false);
                }}
                onRename={onRename}
                onDelete={onDelete}
                onArchive={onArchive}
                onRestore={onRestore}
                onExport={onExport}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-line p-3 text-sm leading-6 text-slate-500">
            {showArchived ? "Các cuộc trò chuyện đã lưu trữ sẽ xuất hiện ở đây." : "Bắt đầu chat mới để tạo cuộc trò chuyện."}
          </div>
        )}
      </div>

      <div className="border-t border-line p-3">
        <div className="mb-2 min-w-0">
          <div className="truncate text-xs font-medium text-slate-700">{user?.display_name ?? "Chưa đăng nhập"}</div>
          <div className="truncate text-xs text-slate-500">{user?.email ?? ""}</div>
          {user ? <div className="mt-1 truncate text-[11px] text-slate-400">{user.role_label}</div> : null}
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="focus-ring inline-flex h-9 w-full items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <LogOut className="h-4 w-4" />
          Đăng xuất
        </button>
      </div>
    </aside>
  );

  return (
    <>
      <button
        type="button"
        onClick={() => onMobileOpenChange(true)}
        title="Open conversations"
        className="focus-ring fixed bottom-4 left-4 z-30 inline-flex h-10 w-10 items-center justify-center rounded-md border border-line bg-white text-slate-700 shadow-sm lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>
      <div className="hidden min-h-0 lg:block">{panel}</div>
      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button type="button" aria-label="Close sidebar" className="absolute inset-0 bg-slate-900/30" onClick={() => onMobileOpenChange(false)} />
          <div className="relative h-full">{panel}</div>
        </div>
      ) : null}
    </>
  );
}

function ConversationRow({
  conversation,
  active,
  archived,
  onSelect,
  onRename,
  onDelete,
  onArchive,
  onRestore,
  onExport
}: {
  conversation: Conversation;
  active: boolean;
  archived: boolean;
  onSelect: (id: string) => void;
  onRename: (id: string) => void;
  onDelete: (id: string) => void;
  onArchive: (id: string) => void;
  onRestore: (id: string) => void;
  onExport: (id: string) => void;
}) {
  return (
    <div className={`group rounded-md ${active ? "bg-cyan-50" : "hover:bg-slate-50"}`}>
      <button
        type="button"
        onClick={() => onSelect(conversation.id)}
        className="focus-ring w-full rounded-md px-3 py-2 text-left text-sm"
      >
        <div className={`truncate font-medium ${active ? "text-cyan-950" : "text-slate-800"}`}>{conversation.title}</div>
        <div className="mt-1 flex items-center justify-between gap-2 text-xs text-slate-500">
          <span className="truncate">{conversation.messages.length} messages</span>
          <span>{formatDate(conversation.updatedAt)}</span>
        </div>
      </button>
      <div className="flex items-center gap-1 px-2 pb-2 opacity-100 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100">
        <IconAction title="Rename" onClick={() => onRename(conversation.id)} icon={Pencil} />
        <IconAction title="Export" onClick={() => onExport(conversation.id)} icon={Download} />
        {archived ? (
          <IconAction title="Restore" onClick={() => onRestore(conversation.id)} icon={RotateCcw} />
        ) : (
          <IconAction title="Archive" onClick={() => onArchive(conversation.id)} icon={Archive} />
        )}
        <IconAction title="Delete" onClick={() => onDelete(conversation.id)} icon={Trash2} danger />
      </div>
    </div>
  );
}

function IconAction({
  title,
  onClick,
  icon: Icon,
  danger
}: {
  title: string;
  onClick: () => void;
  icon: typeof Pencil;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
      className={`focus-ring inline-flex h-7 w-7 items-center justify-center rounded-md ${
        danger ? "text-red-600 hover:bg-red-50" : "text-slate-500 hover:bg-white hover:text-slate-900"
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
    </button>
  );
}
