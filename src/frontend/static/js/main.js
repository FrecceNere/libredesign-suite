document.addEventListener('DOMContentLoaded', async () => {
    const programsContainer = document.getElementById('programs-container');
    const navLinks = document.querySelectorAll('nav a');

    async function loadPrograms(category = 'image_editing') {
        const programs = await window.pywebview.api.get_programs();
        programsContainer.innerHTML = '';
        
        programs[category].forEach(program => {
            const card = document.createElement('div');
            card.className = 'program-card';
            
            const variants = program.variants ? 
                program.variants.map(variant => `
                    <button class="install-button" data-program="${program.name}" data-variant="${variant.type}">
                        <i class="fas fa-download"></i>
                        Install ${variant.name}
                    </button>
                `).join('') :
                `<button class="install-button" data-program="${program.name}">
                    <i class="fas fa-download"></i>
                    Install ${program.name}
                </button>`;

            card.innerHTML = `
                <img src="${program.logo}" alt="${program.name} logo" class="program-logo">
                <div class="program-info">
                    <h2>${program.name}</h2>
                    <div class="program-category">${program.category}</div>
                    <p class="program-description">${program.description}</p>
                    <div class="program-variants">
                        ${variants}
                    </div>
                </div>
            `;
            programsContainer.appendChild(card);
        });

        // Add install button listeners
        document.querySelectorAll('.install-button').forEach(button => {
            button.addEventListener('click', async (e) => {
                const programName = e.target.dataset.program;
                const variant = e.target.dataset.variant || 'apt';
                button.disabled = true;
                button.textContent = 'Installing...';
                
                try {
                    const result = await window.pywebview.api.install_program(programName, variant);
                    if (result.success) {
                        button.textContent = 'Installed';
                        button.classList.add('success');
                    } else {
                        button.textContent = 'Error';
                        button.classList.add('error');
                        alert(result.message);
                    }
                } catch (error) {
                    button.textContent = 'Error';
                    button.classList.add('error');
                    alert('Installation failed');
                }
            });
        });
    }

    // Navigation event listeners
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const category = e.target.dataset.category;
            loadPrograms(category);
            
            navLinks.forEach(l => l.classList.remove('active'));
            e.target.classList.add('active');
        });
    });

    // Load initial programs
    loadPrograms();
});