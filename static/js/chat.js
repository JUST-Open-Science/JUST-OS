function addMessage(message, sender, sources=null) {
    const chatMessages = document.getElementById('chat-messages');

    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);

    if (sender === 'bot') {
        messageDiv.innerHTML = message;
    } else {
        messageDiv.textContent = message;
    }

    if (sources !== null) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.classList.add('sources');
        sourcesDiv.textContent = sources;
        messageDiv.appendChild(sourcesDiv);
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
};

async function sendMessage(message) {
    const chatMessages = document.getElementById('chat-messages');

    console.log('user message: ' + message);
    if (message) {
        const userMessageBox = document.createElement('div');
        userMessageBox.innerText = message;
        userMessageBox.classList.add('message', 'user-message');
        chatMessages.appendChild(userMessageBox);
    }

    const statusMessage = document.getElementById('status-message')
    let baseMessage = "Processing your request";
    statusMessage.innerText = baseMessage;
    let dotCount = 0;
    function updateMessage() {
        dotCount = (dotCount % 4) + 1;
        let newMessage = baseMessage + '.'.repeat(dotCount - 1);
        statusMessage.innerText = newMessage;
    }
    let messageInterval = setInterval(updateMessage, 1000);

    const messageInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    messageInput.disabled = true;
    sendButton.disabled = true;
    sendButton.style.display = 'none';
    window.scrollTo(0, document.body.scrollHeight);

    function endStream() {
        clearInterval(messageInterval);
        messageInput.disabled = false;
        sendButton.style.display = 'block';
        statusMessage.innerText = '';
    }

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message, chat_id: chatId})
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
                    console.log(data.message)

                    if (data.status === 'complete') {
                        endStream();
                        addMessage(data.message, 'bot', data.metadata.sources);
                        
                    } else {
                        baseMessage = data.message;
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error:', error);
        updateStatus('Error: Failed to get response');
    }
    




}

document.addEventListener('DOMContentLoaded', function () {
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    userInput.value = "How does open science reshape the future of interdisciplinary and collaborative research?";

    userInput.addEventListener('input', function() {
        sendButton.disabled = this.value.length < 3;
    });

    userInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            if (!sendButton.disabled) {
                sendButton.click();
            }
        }
    });

    sendButton.addEventListener('click', function() {
        const message = userInput.value;
        userInput.value = '';
        sendMessage(message);
    });
});

function requestBody(message) {
    return JSON.stringify({
        message: message,
        chatId: chatId
    })
}

const chatId = crypto.randomUUID();
