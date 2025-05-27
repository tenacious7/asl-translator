function generateSentence() {
    if (selectedWords.length === 0) {
        showToast('Please collect some words first');
        return;
    }

    const generateBtn = document.getElementById('generateBtn');
    generateBtn.classList.add('loading');
    
    // Clear previous sentence
    document.getElementById('sentenceOutput').textContent = '';
    
    // Emit event to generate sentence
    socket.emit('generate_sentence', { words: selectedWords });
}

socket.on('sentence', function(data) {
    const generateBtn = document.getElementById('generateBtn');
    const sentenceOutput = document.getElementById('sentenceOutput');
    
    generateBtn.classList.remove('loading');
    
    if (data.error) {
        showToast(data.error);
        return;
    }
    
    // Animate sentence appearance
    sentenceOutput.style.opacity = '0';
    setTimeout(() => {
        sentenceOutput.textContent = data.sentence;
        sentenceOutput.style.opacity = '1';
    }, 200);
});

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }, 100);
} 