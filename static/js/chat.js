function addMessage(message, sender) {
    const chatMessages = document.getElementById('chat-messages');

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
        // cancelButton.style.display = 'none';
        // loadingMessageDiv.removeChild(loadingMessageBox);
        // eventSource.close();     
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
                        addMessage(data.message, 'bot');
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




    // function updateStatus(message) {
    //     statusMessage.textContent = message;
    // }

    // function updateLastBotMessage(message) {
    //     const botMessages = document.getElementsByClassName('bot-message');
    //     if (botMessages.length > 0) {
    //         const lastBotMessage = botMessages[botMessages.length - 1];
    //         lastBotMessage.innerHTML = marked.parse(message);
    //     } else {
    //         addMessage(message, 'bot');
    //     }
    //     chatMessages.scrollTop = chatMessages.scrollHeight;
    // }


    // // chat.js
    // async function sendMessage() {
    //     welcomeMessage.textContent = '';

    //     const message = userInput.value.trim();
    //     if (message === '') return;

    //     addMessage(message, 'user');
    //     userInput.value = '';

    //     try {
    //         const response = await fetch('/chat', {
    //             method: 'POST',
    //             headers: {
    //                 'Content-Type': 'application/json',
    //             },
    //             body: JSON.stringify({ message: message })
    //         });

    //         const reader = response.body.getReader();
    //         const decoder = new TextDecoder();

    //         while (true) {
    //             const {value, done} = await reader.read();
    //             if (done) break;

    //             const messages = decoder.decode(value).split('\n');

    //             for (const message of messages) {
    //                 if (message) {  // check for non-empty messages
    //                     const data = JSON.parse(message);
    //                     if (data.status === 'complete') {
    //                         updateStatus('');
    //                         addMessage(data.message, 'bot');
    //                     } else if (data.status === 'generating') {
    //                         addMessage(data.message, 'bot');
    //                     } else {
    //                         updateStatus(data.message);
    //                     }
    //                 }
    //             }
    //         }
    //     } catch (error) {
    //         console.error('Error:', error);
    //         updateStatus('Error: Failed to get response');
    //     }
    // }

    // sendButton.addEventListener('click', sendMessage);
    // userInput.addEventListener('keypress', function (e) {
    //     if (e.key === 'Enter') {
    //         sendMessage();
    //     }
    // });
const chatId = crypto.randomUUID();
console.log(chatId);