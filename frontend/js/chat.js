// TODO: wire the chat form to the FastAPI /chat endpoint with live context.

export function initializeChat(formId = 'chat-form', inputId = 'chat-input', outputId = 'chat-output') {
  const form = document.getElementById(formId);
  const input = document.getElementById(inputId);
  const output = document.getElementById(outputId);

  if (!form || !input || !output) {
    return null;
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    output.textContent = `Consulta recibida: ${input.value.trim() || 'sin texto'}.`;
  });

  return form;
}