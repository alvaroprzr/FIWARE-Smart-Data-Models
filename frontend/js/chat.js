// Chat module: chat panel, message rendering, and API communication.

import { appState, requestJSON, escapeHtml, setConnection, cityLabel } from './utils.js';

/**
 * Add a message to the chat history.
 */
function addChatMessage(role, content) {
  const wrapper = document.createElement('div');
  wrapper.className = `chat-message ${role === 'user' ? 'chat-user' : 'chat-assistant'}`;
  wrapper.textContent = content;
  const chatHistory = document.getElementById('chat-history');
  if (chatHistory) {
    chatHistory.appendChild(wrapper);
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }
  return wrapper;
}

/**
 * Send a chat message to the backend and render the response.
 */
async function sendChat(message) {
  const pending = addChatMessage('assistant', 'Escribiendo...');
  try {
    const response = await requestJSON('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ city: appState.city, message }),
    });
    pending.textContent = response?.response || 'Sin respuesta disponible.';
    setConnection(true, `Conectado · ${cityLabel(appState.city)}`);
  } catch (error) {
    pending.textContent = `Error al responder: ${error.message || 'sin detalle'}`;
    setConnection(false, 'Sin conexión');
  }
}

/**
 * Seed the chat with an initial message.
 */
function seedChat() {
  const chatHistory = document.getElementById('chat-history');
  if (chatHistory) {
    chatHistory.innerHTML = '';
    addChatMessage('assistant', 'Puedo ayudarte con el estado de estaciones, la predicción a 30 y 60 minutos, el clima y las consultas operativas en A Coruña.');
  }
}

/**
 * Initialize the chat module.
 */
export function initChat(city) {
  appState.city = city;
  seedChat();

  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');

  if (chatForm && chatInput) {
    chatForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const message = chatInput.value.trim();
      if (!message) return;
      chatInput.value = '';
      addChatMessage('user', message);
      sendChat(message);
    });
  }

}