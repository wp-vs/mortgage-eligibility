"use client";

import { useEffect, useRef, useState } from "react";
import ChatInput from "@/components/ChatInput";
import ChatMessage from "@/components/ChatMessage";
import BankingConnect from "@/components/BankingConnect";
import { sendMessage, getConversationHistory } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface UIAction {
  type: string;
  auth_url?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [customerId, setCustomerId] = useState<number | null>(null);
  const [bankingUrl, setBankingUrl] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = localStorage.getItem("customerId");
    if (id) {
      setCustomerId(Number(id));
      loadHistory(Number(id));
    } else {
      // Redirect to home to create customer
      window.location.href = "/";
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadHistory(id: number) {
    try {
      const data = await getConversationHistory(id);
      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages);
      }
    } catch {
      // No history yet, that's fine
    }
  }

  async function handleSend(text: string) {
    if (!customerId) return;

    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await sendMessage(customerId, text);

      const assistantMessage: Message = {
        role: "assistant",
        content: response.message,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Handle UI actions (e.g., Open Banking connect)
      if (response.ui_actions) {
        response.ui_actions.forEach((action: UIAction) => {
          if (action.type === "open_banking_connect" && action.auth_url) {
            setBankingUrl(action.auth_url);
          }
        });
      }
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content:
          "I'm sorry, something went wrong. Please try sending your message again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto h-[calc(100vh-73px)] flex flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && !loading && (
          <div className="text-center text-gray-400 mt-20">
            <div className="text-4xl mb-4">👋</div>
            <p className="text-lg">
              Welcome! Send a message to start exploring your mortgage options.
            </p>
            <p className="text-sm mt-2">
              Try: &quot;I&apos;m looking to buy my first home&quot;
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} role={msg.role} content={msg.content} />
        ))}

        {bankingUrl && <BankingConnect authUrl={bankingUrl} />}

        {loading && (
          <div className="flex justify-start mb-4">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-5 py-3 shadow-sm">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <span
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                />
                <span
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white px-4 py-4">
        <ChatInput onSend={handleSend} disabled={loading} />
        <p className="text-xs text-gray-400 text-center mt-2">
          This is an information service, not financial advice. A broker will
          review your case.
        </p>
      </div>
    </div>
  );
}
