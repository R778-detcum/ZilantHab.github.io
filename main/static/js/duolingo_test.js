// duolingo_test.js – с анимациями и звуками (опционально)

let currentQuestionIndex = 0;
let questionsData = [];
let userLives = 5;
let timerInterval = null;
let timeLeft = 30;
let canAnswer = true;
let currentDragItem = null;
let audioCorrect = null;
let audioWrong = null;

window.duolingoInit = function(questionsJson, lessonId, csrfToken) {
    questionsData = questionsJson;
    window.lessonId = lessonId;
    window.csrfToken = csrfToken;
    currentQuestionIndex = 0;
    userLives = 5;
    updateLivesDisplay();
    loadQuestion(0);
    // Предзагружаем звуки, если хотите (файлы должны лежать в static/sounds/)
    // audioCorrect = new Audio('/static/sounds/correct.mp3');
    // audioWrong = new Audio('/static/sounds/wrong.mp3');
};

function updateLivesDisplay() {
    const container = document.getElementById('lives-container');
    if (!container) return;
    container.innerHTML = '';
    for (let i = 0; i < 5; i++) {
        const heart = document.createElement('i');
        heart.className = i < userLives ? 'fas fa-heart heart' : 'fas fa-heart heart heart-lost';
        container.appendChild(heart);
    }
    if (userLives <= 0) {
        disableTestAndShowRestore();
    }
}

function disableTestAndShowRestore() {
    canAnswer = false;
    if (timerInterval) clearInterval(timerInterval);
    document.querySelectorAll('.option-btn, .drag-word, .drop-zone, .translate-input, .btn-submit-test').forEach(el => {
        if (el) el.style.pointerEvents = 'none';
    });
    alert('❤️ Жизни закончились! Урок не засчитан. Попробуйте ещё раз позже.');
    window.location.href = window.location.href.replace('/test/', '/');
}

function loadQuestion(index) {
    if (!canAnswer) return;
    if (index >= questionsData.length) {
        submitTestFinal();
        return;
    }
    const q = questionsData[index];
    document.getElementById('question-text').innerHTML = q.text;
    document.getElementById('question-counter').innerText = `${index+1} / ${questionsData.length}`;

    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = '';

    if (q.question_type === 'choice' || q.question_type === 'audio_choice') {
        q.options.forEach((opt, idx) => {
            const btn = document.createElement('div');
            btn.className = 'option-btn';
            btn.setAttribute('data-value', idx+1);
            btn.innerHTML = `<span class="option-letter">${String.fromCharCode(65+idx)}</span> ${opt}`;
            btn.onclick = () => selectOption(btn, q.id, idx+1);
            optionsContainer.appendChild(btn);
        });
    } else if (q.question_type === 'translate') {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'translate-input';
        input.placeholder = 'Введите перевод...';
        input.id = 'translate-input';
        const btn = document.createElement('button');
        btn.className = 'btn-submit-test';
        btn.innerText = 'Проверить';
        btn.onclick = () => checkTranslate(q.id, input.value);
        optionsContainer.appendChild(input);
        optionsContainer.appendChild(btn);
    } else if (q.question_type === 'match') {
        const leftWords = q.left_items;
        const rightWords = q.right_items;
        const dragArea = document.createElement('div');
        dragArea.className = 'drag-drop-area';
        const dropArea = document.createElement('div');
        dropArea.className = 'drag-drop-area';
        leftWords.forEach(word => {
            const draggable = document.createElement('div');
            draggable.className = 'drag-word';
            draggable.setAttribute('draggable', 'true');
            draggable.innerText = word;
            draggable.ondragstart = (e) => {
                currentDragItem = word;
                e.dataTransfer.setData('text/plain', word);
            };
            dragArea.appendChild(draggable);
        });
        rightWords.forEach((translation, idx) => {
            const zone = document.createElement('div');
            zone.className = 'drop-zone';
            zone.innerText = translation;
            zone.ondragover = (e) => e.preventDefault();
            zone.ondrop = (e) => {
                e.preventDefault();
                const droppedWord = currentDragItem;
                if (droppedWord && isMatchCorrect(droppedWord, translation, q)) {
                    zone.classList.add('dropped');
                    zone.style.background = '#dcfce7';
                    zone.innerText = translation + ' ✓';
                    zone.style.pointerEvents = 'none';
                    checkMatchComplete(q.id);
                } else {
                    zone.classList.add('wrong-shake');
                    setTimeout(() => zone.classList.remove('wrong-shake'), 300);
                    loseLifeAndRetry();
                }
                currentDragItem = null;
            };
            dropArea.appendChild(zone);
        });
        optionsContainer.appendChild(dragArea);
        optionsContainer.appendChild(dropArea);
    }
    resetTimer(q.time_limit || 30);
}

function resetTimer(seconds) {
    if (timerInterval) clearInterval(timerInterval);
    timeLeft = seconds;
    const timerBar = document.getElementById('timer-progress');
    const timerText = document.getElementById('timer-text');
    if (timerText) timerText.innerText = timeLeft;
    if (timerBar) {
        timerBar.style.width = '100%';
        timerBar.classList.remove('warning', 'danger');
    }
    timerInterval = setInterval(() => {
        if (!canAnswer) return;
        timeLeft--;
        if (timerText) timerText.innerText = timeLeft;
        if (timerBar) {
            const percent = (timeLeft / seconds) * 100;
            timerBar.style.width = `${percent}%`;
            if (percent < 30) {
                timerBar.classList.add('danger');
                timerBar.classList.remove('warning');
            } else if (percent < 60) {
                timerBar.classList.add('warning');
                timerBar.classList.remove('danger');
            }
        }
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            handleTimeOut();
        }
    }, 1000);
}

function handleTimeOut() {
    if (!canAnswer) return;
    loseLifeAndRetry();
}

function loseLifeAndRetry() {
    userLives--;
    updateLivesDisplay();
    if (audioWrong) audioWrong.play();
    if (userLives <= 0) {
        disableTestAndShowRestore();
        return;
    }
    showHintAndReload();
}

function showHintAndReload() {
    const q = questionsData[currentQuestionIndex];
    if (q.explanation) {
        alert(`💡 Подсказка: ${q.explanation}`);
    }
    loadQuestion(currentQuestionIndex);
}

function selectOption(btn, questionId, selectedValue) {
    if (!canAnswer) return;
    fetch('/api/check-answer/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrfToken },
        body: JSON.stringify({ question_id: questionId, selected: selectedValue })
    })
    .then(res => res.json())
    .then(data => {
        if (data.correct) {
            if (audioCorrect) audioCorrect.play();
            btn.classList.add('correct-glow');
            setTimeout(() => {
                currentQuestionIndex++;
                loadQuestion(currentQuestionIndex);
            }, 500);
        } else {
            if (audioWrong) audioWrong.play();
            btn.classList.add('wrong-shake');
            setTimeout(() => btn.classList.remove('wrong-shake'), 300);
            loseLifeAndRetry();
        }
    });
}

function checkTranslate(questionId, userAnswer) {
    if (!canAnswer) return;
    fetch('/api/check-answer/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrfToken },
        body: JSON.stringify({ question_id: questionId, answer_text: userAnswer })
    })
    .then(res => res.json())
    .then(data => {
        if (data.correct) {
            if (audioCorrect) audioCorrect.play();
            const input = document.getElementById('translate-input');
            if (input) input.classList.add('correct-glow');
            setTimeout(() => {
                currentQuestionIndex++;
                loadQuestion(currentQuestionIndex);
            }, 500);
        } else {
            if (audioWrong) audioWrong.play();
            loseLifeAndRetry();
        }
    });
}

function isMatchCorrect(droppedWord, translation, question) {
    // упрощённая проверка: правильная пара – первый элемент списка left_items с соответствующим right_items
    const idx = question.left_items.indexOf(droppedWord);
    if (idx !== -1 && question.right_items[idx] === translation) return true;
    return false;
}

function checkMatchComplete(questionId) {
    // проверяем, все ли зоны заполнены
    const dropZones = document.querySelectorAll('.drop-zone');
    let allFilled = true;
    dropZones.forEach(zone => {
        if (!zone.classList.contains('dropped')) allFilled = false;
    });
    if (allFilled) {
        if (audioCorrect) audioCorrect.play();
        setTimeout(() => {
            currentQuestionIndex++;
            loadQuestion(currentQuestionIndex);
        }, 500);
    }
}

function submitTestFinal() {
    fetch('/lesson/' + window.lessonId + '/test/submit/', {
        method: 'POST',
        headers: { 'X-CSRFToken': window.csrfToken, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ 'final_score': '1' })
    })
    .then(res => res.json())
    .then(data => {
        if (data.passed) {
            launchConfetti();
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 2000);
        } else {
            alert('Тест не пройден. Попробуйте ещё раз.');
            window.location.reload();
        }
    });
}

function launchConfetti() {
    if (typeof confetti === 'function') {
        confetti({ particleCount: 200, spread: 80, origin: { y: 0.6 }, startVelocity: 20 });
    }
}