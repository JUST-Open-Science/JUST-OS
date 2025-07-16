function setupReferenceHandlers() {
  document.querySelectorAll(".reference-link").forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      // Remove any existing tooltips
      document
        .querySelectorAll(".reference-tooltip")
        .forEach((t) => t.remove());

      // Create tooltip
      const tooltip = document.createElement("div");
      tooltip.className = "reference-tooltip";

      const data = JSON.parse(this.getAttribute("data-reference"));

      tooltip.innerHTML = `
                <div class="title">${data.title}</div>
                <div class="metadata">${data.authors} (${data.year})</div>
                <div class="content">${data.text}</div>
                ${
                  data.url
                    ? `<a href="${data.url}" target="_blank" class="source-link">View source →</a>`
                    : ""
                }
            `;

      // Position tooltip near the click
      const rect = this.getBoundingClientRect();
      const tooltipX = Math.min(
        rect.left,
        window.innerWidth - 520 // account for tooltip width + margin
      );

      tooltip.style.left = `${tooltipX}px`;
      tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;

      // Add tooltip to document
      document.body.appendChild(tooltip);

      // Adjust position if tooltip goes off-screen
      const tooltipRect = tooltip.getBoundingClientRect();
      if (tooltipRect.right > window.innerWidth) {
        tooltip.style.left = `${window.innerWidth - tooltipRect.width - 20}px`;
      }
      if (tooltipRect.bottom > window.innerHeight) {
        tooltip.style.top = `${
          rect.top + window.scrollY - tooltipRect.height - 5
        }px`;
      }

      // Close tooltip when clicking outside
      function closeTooltip(e) {
        if (!tooltip.contains(e.target) && e.target !== link) {
          tooltip.remove();
          document.removeEventListener("click", closeTooltip);
        }
      }

      // Add delay before adding click listener to prevent immediate closing
      setTimeout(() => {
        document.addEventListener("click", closeTooltip);
      }, 0);
    });
  });
}

function addMessage(message, sender, sources = null) {
  const chatMessages = document.getElementById("chat-messages");

  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", `${sender}-message`);

  if (sender === "bot") {
    messageDiv.innerHTML = message;
    // Setup reference handlers after adding bot message
    setTimeout(() => {
      setupReferenceHandlers();
    }, 0);
  } else {
    messageDiv.textContent = message;
  }

  if (sources !== null) {
    const sourcesDiv = document.createElement("div");
    sourcesDiv.classList.add("sources");
    sourcesDiv.textContent = sources;
    messageDiv.appendChild(sourcesDiv);
  }

  chatMessages.appendChild(messageDiv);

  // If this is a bot message, scroll the previous user message to the top
  if (sender === "bot") {
    const messages = chatMessages.getElementsByClassName("message");
    const lastUserMessage = Array.from(messages)
      .reverse()
      .find((msg) => msg.classList.contains("user-message"));
    if (lastUserMessage) {
      const rect = lastUserMessage.getBoundingClientRect();
      const absoluteTop = window.scrollY + rect.top - 20; // 20px padding from top
      console.log("Scrolling to:", absoluteTop);
      window.scrollTo({
        top: absoluteTop,
        behavior: "smooth",
      });
    }
  }
}

async function sendMessage(message) {
  const chatMessages = document.getElementById("chat-messages");

  console.log("user message: " + message);
  if (message) {
    const userMessageBox = document.createElement("div");
    const messageP = document.createElement("p");
    messageP.innerText = message;
    userMessageBox.appendChild(messageP);
    userMessageBox.classList.add("message", "user-message");
    chatMessages.appendChild(userMessageBox);
  }

  const statusMessage = document.getElementById("status-message");
  let baseMessage = "Processing your request";
  statusMessage.innerText = baseMessage;
  let dotCount = 0;
  function updateMessage() {
    dotCount = (dotCount % 4) + 1;
    let newMessage = baseMessage + ".".repeat(dotCount - 1);
    statusMessage.innerText = newMessage;
  }
  let messageInterval = setInterval(updateMessage, 1000);

  const messageInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");

  messageInput.disabled = true;
  sendButton.disabled = true;
  //  sendButton.style.display = "none";
  window.scrollTo(0, document.body.scrollHeight, { behavior: "smooth" });

  function endStream() {
    clearInterval(messageInterval);
    messageInput.disabled = false;
    sendButton.style.display = "block";
    statusMessage.innerText = "";
  }

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: message, chat_id: window.chatId }),
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete messages
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
        const message = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);

        if (message) {
          // check for non-empty messages
          try {
            console.log("Received message:", message);
            const data = JSON.parse(message);

            if (data.status === "complete") {
              endStream();
              addMessage(data.message, "bot");
            } else {
              baseMessage = data.message;
            }
          } catch (parseError) {
            console.warn("Failed to parse message:", parseError);
            // Add the failed message back to the buffer
            buffer = message + "\n" + buffer;
            break;
          }
        }
      }
    }

    // Process any remaining data in the buffer
    if (buffer.trim()) {
      try {
        console.log("Processing remaining buffer:", buffer);
        const data = JSON.parse(buffer);
        if (data.status === "complete") {
          endStream();
          addMessage(data.message, "bot");
        } else {
          baseMessage = data.message;
        }
      } catch (parseError) {
        console.warn("Failed to parse final buffer:", parseError);
      }
    }
  } catch (error) {
    console.error("Error:", error);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  // Add CSS for new elements
  const style = document.createElement('style');
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");
  const infoButton = document.getElementById("info-button");
  const newChatButton = document.getElementById("new-chat-button");
  const modal = document.getElementById("info-modal");
  const closeModal = document.querySelector(".close-modal");

  userInput.value =
    "How does open science reshape the future of interdisciplinary and collaborative research?";

  userInput.addEventListener("input", function () {
    sendButton.disabled = this.value.length < 3;
  });

  userInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!sendButton.disabled) {
        sendButton.click();
      }
    }
  });

  sendButton.addEventListener("click", function () {
    const message = userInput.value;
    userInput.value = "";
    sendMessage(message);
  });

  // Modal functionality
  infoButton.addEventListener("click", function () {
    modal.style.display = "block";
  });

  closeModal.addEventListener("click", function () {
    modal.style.display = "none";
  });

  window.addEventListener("click", function (event) {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  });
  
  // New chat button functionality
  newChatButton.addEventListener("click", function() {
    // Clear chat messages
    const chatMessages = document.getElementById("chat-messages");
    chatMessages.innerHTML = "";
    
    // Generate a new chat ID
    window.chatId = crypto.randomUUID();
    
    // Reset the input field with the default question
    userInput.value = "How does open science reshape the future of interdisciplinary and collaborative research?";
    
  });
});

function requestBody(message) {
  return JSON.stringify({
    message: message,
    chatId: window.chatId,
  });
}

// Initialize chatId as a global variable
window.chatId = crypto.randomUUID();
