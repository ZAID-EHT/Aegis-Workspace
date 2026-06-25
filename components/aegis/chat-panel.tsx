"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MessageSquare, Send, X } from "lucide-react";

import { createClient } from "@/lib/supabase/client";

interface Message {
  id: string;
  team_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  created_at: string;
}

interface ChatPanelProps {
  teamId: string;
  currentUserId: string;
  currentUserName: string;
  isReadOnly: boolean;
  messageLimit?: number;
}

export function ChatPanel({
  teamId,
  currentUserId,
  currentUserName,
  isReadOnly,
  messageLimit = 50,
}: ChatPanelProps) {
  const supabase = React.useMemo(() => createClient(), []);
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [inputValue, setInputValue] = React.useState("");
  const [sending, setSending] = React.useState(false);
  const [sendError, setSendError] = React.useState<string | null>(null);
  const [isConnected, setIsConnected] = React.useState(false);
  const [userScrolledUp, setUserScrolledUp] = React.useState(false);
  const bottomRef = React.useRef<HTMLDivElement>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const channelRef = React.useRef<any>(null);

  React.useEffect(() => {
    let active = true;
    setIsConnected(false);

    void supabase
      .from("messages")
      .select("*")
      .eq("team_id", teamId)
      .order("created_at", { ascending: true })
      .limit(messageLimit)
      .then(({ data, error }) => {
        if (!active) return;
        if (error) return;
        if (data) setMessages(data as Message[]);
      });

    const channel = supabase
      .channel(`team-chat-${teamId}`)
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "messages", filter: `team_id=eq.${teamId}` },
        (payload) => {
          setMessages((current) => [...current, payload.new as Message]);
        },
      )
      .subscribe((status) => {
        setIsConnected(status === "SUBSCRIBED");
      });

    channelRef.current = channel;

    return () => {
      active = false;
      void channelRef.current?.unsubscribe();
      channelRef.current = null;
    };
  }, [messageLimit, supabase, teamId]);

  React.useEffect(() => {
    if (!userScrolledUp && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, userScrolledUp]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setUserScrolledUp(distanceFromBottom > 80);
  };

  const send = async () => {
    const content = inputValue.trim();
    if (!content || sending) return;

    setSending(true);
    setSendError(null);

    const { error } = await supabase.from("messages").insert({
      team_id: teamId,
      sender_id: currentUserId,
      sender_name: currentUserName,
      content,
    });

    if (error) {
      setSendError(error.message);
      setSending(false);
      return;
    }

    setInputValue("");
    setSending(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  };

  return (
    <div
      style={{
        height: isReadOnly ? 240 : 320,
        display: "flex",
        flexDirection: "column",
        borderRadius: "1.5rem",
        border: "1px solid var(--border)",
        background: "var(--card)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: 48,
          borderBottom: "1px solid var(--border)",
          padding: "0 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <MessageSquare size={15} color="var(--foreground)" />
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>Team chat</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: 9999,
              background: isConnected ? "#10B981" : "var(--muted-foreground)",
            }}
          />
          <span style={{ fontSize: 11, color: "var(--muted-foreground)" }}>
            {isConnected ? "Live" : "Connecting"}
          </span>
        </div>
      </div>

      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 16px",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              minHeight: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--muted-foreground)",
              fontSize: 13,
              textAlign: "center",
            }}
          >
            No messages yet. Start the conversation.
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((message, index) => {
              const isOwn = message.sender_id === currentUserId;
              const isFirstInGroup = index === 0 || messages[index - 1]?.sender_id !== message.sender_id;
              return (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 1, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isOwn ? "flex-end" : "flex-start",
                  }}
                >
                  {isFirstInGroup && !isOwn && (
                    <span
                      style={{
                        marginBottom: 2,
                        fontSize: 11,
                        fontWeight: 600,
                        color: "var(--muted-foreground)",
                      }}
                    >
                      {message.sender_name}
                    </span>
                  )}
                  <div
                    style={{
                      maxWidth: "75%",
                      padding: "8px 12px",
                      borderRadius: 12,
                      background: isOwn
                        ? "color-mix(in oklch, var(--primary) 15%, transparent)"
                        : "var(--muted)",
                      border: isOwn
                        ? "1px solid color-mix(in oklch, var(--primary) 30%, transparent)"
                        : "1px solid var(--border)",
                    }}
                  >
                    <p
                      style={{
                        fontSize: 13,
                        lineHeight: 1.5,
                        color: "var(--foreground)",
                        wordBreak: "break-word",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {message.content}
                    </p>
                  </div>
                  <span
                    style={{
                      marginTop: 2,
                      fontSize: 10,
                      color: "var(--muted-foreground)",
                      fontFamily: "monospace",
                    }}
                  >
                    {new Date(message.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
        <div ref={bottomRef} style={{ height: 1 }} />
      </div>

      {sendError && (
        <div
          style={{
            background: "color-mix(in oklch, #EF4444 10%, transparent)",
            border: "1px solid color-mix(in oklch, #EF4444 30%, transparent)",
            padding: "6px 12px",
            fontSize: 12,
            color: "#EF4444",
            borderRadius: 6,
            margin: "0 16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span>Could not send. Tap send to try again.</span>
          <button type="button" onClick={() => setSendError(null)} aria-label="Dismiss send error">
            <X size={13} />
          </button>
        </div>
      )}

      {isReadOnly ? (
        <div
          style={{
            padding: "8px 16px",
            fontSize: 11,
            color: "var(--muted-foreground)",
            textAlign: "center",
            borderTop: "1px solid var(--border)",
          }}
        >
          Monitoring view. Students post here.
        </div>
      ) : (
        <div
          style={{
            borderTop: "1px solid var(--border)",
            padding: "10px 12px",
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          <input
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sending}
            placeholder="Message your team"
            style={{
              flex: 1,
              height: 38,
              borderRadius: 9999,
              border: "1px solid var(--border)",
              background: "var(--background)",
              padding: "0 14px",
              fontSize: 13,
              color: "var(--foreground)",
              minWidth: 0,
            }}
          />
          <button
            type="button"
            disabled={!inputValue.trim() || sending}
            onClick={() => void send()}
            aria-label="Send message"
            style={{
              width: 38,
              height: 38,
              flexShrink: 0,
              borderRadius: 9999,
              background: "var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              opacity: !inputValue.trim() || sending ? 0.4 : 1,
              cursor: !inputValue.trim() || sending ? "not-allowed" : "pointer",
            }}
          >
            <Send size={15} color="white" />
          </button>
        </div>
      )}
    </div>
  );
}
