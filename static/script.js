document.addEventListener("DOMContentLoaded", function () {
    const note = document.getElementById("note");
    const noteContent = document.getElementById("note-content");
    const messageInput = document.getElementById("messageInput");
    const feedbackMessage = document.getElementById("feedback-message");
    const remainingChancesElement = document.getElementById("remaining-chances");
    const sendButton = document.getElementById("sendButton");
    
    let remainingChances = parseInt(remainingChancesElement?.dataset.remainingChances || 0);

    if (note) {
        note.addEventListener("click", function () {
            note.classList.add("hidden");
            noteContent.classList.remove("hidden");
        });
    }

    if (sendButton) {
        sendButton.addEventListener("click", function () {
            const message = messageInput.value.trim();
            if (!message) {
                feedbackMessage.textContent = "❌ Please enter a message.";
                feedbackMessage.classList.remove("hidden");
                return;
            }

            fetch(sendButton.dataset.url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ message: message }),
            })
                .then((response) => response.json())
                .then((data) => {
                    if (data.success) {
                        remainingChances = data.remaining_chances;
                        feedbackMessage.textContent = "📩 Your question has been sent successfully!";
                        remainingChancesElement.textContent = `익명으로 질문을 남길 ${remainingChances}번의 기회가 남았습니다.`;
                        sendButton.disabled = remainingChances === 0;
                    } else {
                        feedbackMessage.textContent = data.error || "❌ Error occurred.";
                    }
                    feedbackMessage.classList.remove("hidden");
                    messageInput.value = "";
                })
                .catch((error) => {
                    feedbackMessage.textContent = "❌ Error sending question. Please try again!";
                    feedbackMessage.classList.remove("hidden");
                    console.error("Error:", error);
                });
        });
    }

    // Prevent Join the Party from redirecting before processing
    const joinForm = document.querySelector("form");
    if (joinForm) {
        joinForm.addEventListener("submit", function (event) {
            event.preventDefault();
            let formData = new FormData(this);
            fetch(this.action, {
                method: "POST",
                body: formData
            }).then(response => response.text())
            .then(text => {
                if (text.includes("이미 등록되었습니다")) {
                    alert("이미 등록되었습니다. 로그인을 해주세요.");
                    window.location.href = "/login";
                } else {
                    alert("참가 등록 완료! 모든 참가자가 등록되면 이메일이 발송됩니다.");
                    window.location.reload();
                }
            });
        });
    }
});
