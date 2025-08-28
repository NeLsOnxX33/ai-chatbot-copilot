let isTyping = false;
let currentSessionId = null;
let historyLoaded = false; // Flag to track if history has been loaded
let selectedRating = 0;

function getOrCreateSessionId() {
  try {
    let sessionId = window.localStorage?.getItem('chatbot_session_id');
    console.log(sessionId);
    if (!sessionId) {
      return createNewSession();
    }
    return sessionId;
  } catch (error) {
    console.warn("localStorage not available, using temporary session");
    return 'temp_session_' + Date.now();
  }
}

async function createNewSession() {
  try {
    const response = await fetch("http://127.0.0.1:8000/chat/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    if (response.ok) {
      const data = await response.json();
      try {
        window.localStorage?.setItem('chatbot_session_id', data.session_id);
      } catch (e) {
        console.warn("Could not save session to localStorage");
      }
      return data.session_id;
    }
  } catch (error) {
    console.log("Session error:", error);
  }
  return 'fallback_session_' + Date.now();
}

function renderMessage(message, sender) {
  const chat = document.getElementById("chat-body");
  const iconUrl = sender === 'user'
    ? 'https://cdn-icons-png.flaticon.com/512/1144/1144760.png'
    : 'https://cdn-icons-png.flaticon.com/512/4712/4712100.png';

  const msgHTML = `
    <div class="message ${sender}">
      <img src="${iconUrl}" alt="${sender}" />
      <div class="text">${sender === 'user' ? escapeHtml(message) : message}</div>
    </div>
  `;
  chat.innerHTML += msgHTML;
}

async function loadChatHistory() {
  if (!currentSessionId || historyLoaded) return;
  
  try {
    const response = await fetch(`http://127.0.0.1:8000/chat/history/${currentSessionId}`);
    const chat = document.getElementById("chat-body");
    
    if (response.ok) {
      const data = await response.json();
      // Only clear if we're going to show something new
      if (data.messages && data.messages.length > 0) {
        chat.innerHTML = ''; // Clear only when we have messages to show
        data.messages.forEach(msg => {
          renderMessage(msg.message, msg.sender);
        });
        historyLoaded = true;
      } else if (!historyLoaded) {
        // Only show welcome message if no history exists and we haven't loaded before
        showWelcomeMessage();
        historyLoaded = true;
      }
    } else if (!historyLoaded) {
      showWelcomeMessage();
      historyLoaded = true;
    }
    scrollToBottom();
  } catch (error) {
    console.error("Load error:", error);
    if (!historyLoaded) {
      showWelcomeMessage();
      historyLoaded = true;
    }
  }
}

function showWelcomeMessage() {
  const chat = document.getElementById("chat-body");
  chat.innerHTML = `
    <div class="welcome-message">
      <h4>Hello There! 👋</h4>
      <p>I'm your AI ChatBot. How can I help you today?</p>
    </div>
  `;
}

function closeChat() {
  const popup = document.getElementById('chatbot-popup');
  const toggle = document.getElementById('chatbot-toggle');
  const feedbackForm = document.getElementById('feedback-form');

  if (popup && toggle) {
    popup.classList.remove('active');
    popup.classList.add('inactive');
    toggle.classList.remove('active');
    toggle.classList.remove('inactive');
    document.body.classList.remove('chatbot-open');
    
    // Hide feedback form when closing chat
    if (feedbackForm) {
      feedbackForm.classList.remove('active');
      feedbackForm.classList.add('inactive');
    }
  }
}

function openChat() {
  const popup = document.getElementById('chatbot-popup');
  const toggle = document.getElementById('chatbot-toggle');

  if (popup && toggle) {
    popup.classList.remove('inactive');
    popup.classList.add('active');
    toggle.classList.add('inactive');
    document.body.classList.add('chatbot-open');

    // Load history only when opening chat and if not already loaded
    if (!historyLoaded) {
      loadChatHistory();
    }

    setTimeout(() => {
      window.getComputedStyle(popup).right;
    }, 100);
  }
}

function toggleFeedbackForm() {
  const feedbackForm = document.getElementById('feedback-form');
  const chatBody = document.getElementById('chat-body');
  const chatInput = document.querySelector('.chat-input');
  
  if (feedbackForm.classList.contains('inactive')) {
    // Show feedback form
    feedbackForm.classList.remove('inactive');
    feedbackForm.classList.add('active');
    // Hide chat body and input
    chatBody.style.display = 'none';
    chatInput.style.display = 'none';
  } else {
    // Hide feedback form
    feedbackForm.classList.remove('active');
    feedbackForm.classList.add('inactive');
    // Show chat body and input
    chatBody.style.display = 'flex';
    chatInput.style.display = 'flex';
  }
}

function closeFeedbackForm() {
  const feedbackForm = document.getElementById('feedback-form');
  const chatBody = document.getElementById('chat-body');
  const chatInput = document.querySelector('.chat-input');
  
  // Hide feedback form
  feedbackForm.classList.remove('active');
  feedbackForm.classList.add('inactive');
  // Show chat body and input
  chatBody.style.display = 'flex';
  chatInput.style.display = 'flex';
  
  // Reset form
  resetFeedbackForm();
}

function resetFeedbackForm() {
  selectedRating = 0;
  document.querySelectorAll('.rating-stars span').forEach(s => s.classList.remove('selected'));
  document.getElementById('feedback-comment').value = '';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function scrollToBottom() {
  const chatBody = document.getElementById("chat-body");
  if (chatBody) {
    chatBody.scrollTop = chatBody.scrollHeight;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    currentSessionId = await getOrCreateSessionId();
    console.log("Session ID:", currentSessionId);

    // Load chat history immediately on page load
    await loadChatHistory();

    const popup = document.getElementById('chatbot-popup');
    const toggle = document.getElementById('chatbot-toggle');
    const closeBtn = document.getElementById('chatbot-close');
    const sendBtn = document.getElementById('send-btn');
    const userInput = document.getElementById('user-input');
    const clearBtn = document.getElementById('clear-history-btn');
    const feedbackToggleBtn = document.getElementById('feedback-toggle');
    const submitFeedbackBtn = document.getElementById('submit-feedback-btn');
    const cancelFeedbackBtn = document.getElementById('cancel-feedback-btn');

    if (toggle) {
      toggle.addEventListener('click', async (e) => {
        e.preventDefault();
        if (popup.classList.contains('inactive')) {
          openChat();
        } else {
          closeChat();
        }
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        closeChat();
      });
    }

    if (sendBtn) {
      sendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        sendMessage();
      });
    }

    if (userInput) {
      userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          sendMessage();
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', clearChatHistory);
    }

    // Feedback form event listeners
    if (feedbackToggleBtn) {
      feedbackToggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        toggleFeedbackForm();
      });
    }

    if (submitFeedbackBtn) {
      submitFeedbackBtn.addEventListener('click', submitFeedback);
    }

    if (cancelFeedbackBtn) {
      cancelFeedbackBtn.addEventListener('click', (e) => {
        e.preventDefault();
        closeFeedbackForm();
      });
    }

    // Rating stars event listeners
    document.querySelectorAll('.rating-stars span').forEach(star => {
      star.addEventListener('click', () => {
        selectedRating = parseInt(star.dataset.star);
        document.querySelectorAll('.rating-stars span').forEach(s => s.classList.remove('selected'));
        for (let i = 0; i < selectedRating; i++) {
          document.querySelectorAll('.rating-stars span')[i].classList.add('selected');
        }
      });
    });

  } catch (error) {
    console.error("Initialization error:", error);
  }
});

async function sendMessage() {
  const input = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const message = input.value.trim();

  if (!message || isTyping) return;

  input.value = "";
  isTyping = true;
  input.disabled = true;
  sendBtn.disabled = true;

  renderMessage(message, 'user');
  showTypingIndicator();

  try {
    const response = await fetch("http://127.0.0.1:8000/chat/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message, session_id: currentSessionId })
    });

    const data = await response.json();
    removeTypingIndicator();

    const botMessage = data.reply || data.response || 'No response received';
    renderMessage(botMessage, 'bot');

  } catch (error) {
    console.error("Send error:", error);
    removeTypingIndicator();
    renderMessage("Error: Unable to connect to the server. Please try again later.", 'bot');
  } finally {
    isTyping = false;
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
    scrollToBottom();
  }
}

function showTypingIndicator() {
  const chat = document.getElementById("chat-body");
  chat.innerHTML += `<div class="typing-indicator">AI is thinking...</div>`;
  scrollToBottom();
}

function removeTypingIndicator() {
  const indicator = document.querySelector(".typing-indicator");
  if (indicator) {
    indicator.remove();
  }
}

async function clearChatHistory() {
  if (!currentSessionId) return;
  
  // Show confirmation dialog
  const confirmClear = confirm("Are you sure you want to clear the chat history? This action cannot be undone.");
  if (!confirmClear) return;

  try {
    const response = await fetch(`http://127.0.0.1:8000/chat/clear/${currentSessionId}`, {
      method: "DELETE"
    });
    
    if (response.ok) {
      // Reset the history loaded flag and clear the chat
      historyLoaded = false;
      showWelcomeMessage();
      historyLoaded = true; // Set to true to prevent auto-loading
      console.log("Chat history cleared successfully");
    } else {
      console.error("Failed to clear chat history");
      alert("Failed to clear chat history. Please try again.");
    }
  } catch (error) {
    console.error("Clear history error:", error);
    alert("Error clearing chat history. Please try again.");
  }
}

async function submitFeedback() {
  const comment = document.getElementById('feedback-comment').value;

  if (!selectedRating && comment.trim() === "") {
    alert("Please select a rating or write a comment.");
    return;
  }

  try {
    const response = await fetch("http://127.0.0.1:8000/chat/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        rating: selectedRating,
        comment: comment
      })
    });

    if (response.ok) {
      // Show success message in chat
      renderMessage("Thank you for your feedback! 🙏", "bot");
      
      // Close feedback form and reset
      closeFeedbackForm();
      
      console.log("Feedback submitted successfully");
    } else {
      alert("Failed to submit feedback. Please try again.");
    }
  } catch (error) {
    console.error("Feedback error:", error);
    alert("Error submitting feedback. Please try again.");
  }
}