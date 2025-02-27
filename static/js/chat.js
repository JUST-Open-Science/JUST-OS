document.addEventListener('DOMContentLoaded', function () {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const statusMessage = document.getElementById('status-message');

    userInput.value = "How does open science reshape the future of interdisciplinary and collaborative research?";


    marked.setOptions({
        breaks: true,  // Convert \n to <br>
        gfm: true,     // GitHub Flavored Markdown
        sanitize: false // Allow HTML in the markdown
    });

    // Add welcome message
    addMessage(welcomeMessage, 'bot');

    function addMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);
        
        // Only render markdown for bot messages
        if (sender === 'bot') {
            messageDiv.innerHTML = marked.parse(message);
        } else {
            messageDiv.textContent = message;
        }
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function updateStatus(message) {
        statusMessage.textContent = message;
    }

    function updateLastBotMessage(message) {
        const botMessages = document.getElementsByClassName('bot-message');
        if (botMessages.length > 0) {
            const lastBotMessage = botMessages[botMessages.length - 1];
            lastBotMessage.innerHTML = marked.parse(message);
        } else {
            addMessage(message, 'bot');
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }


    // chat.js
    async function sendMessage() {
        const message = userInput.value.trim();
        if (message === '') return;

        addMessage(message, 'user');
        userInput.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const {value, done} = await reader.read();
                if (done) break;

                const messages = decoder.decode(value).split('\n');

                for (const message of messages) {
                    if (message) {  // check for non-empty messages
                        const data = JSON.parse(message);
                        if (data.status === 'complete') {
                            updateStatus('');
                            addMessage(data.message, 'bot');
                        } else if (data.status === 'generating') {
                            addMessage(data.message, 'bot');
                        } else {
                            updateStatus(data.message);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error);
            updateStatus('Error: Failed to get response');
        }
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
