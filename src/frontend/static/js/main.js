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
                    <button class="install-button ${variant.installed ? 'success' : ''}" 
                            data-program="${program.name}" 
                            data-variant="${variant.type}"
                            ${variant.installed ? 'disabled' : ''}>
                        <i class="fas ${variant.installed ? 'fa-check' : 'fa-download'}"></i>
                        <span class="button-text">
                            ${variant.installed ? 'Installed' : `Install ${variant.name}`}
                        </span>
                        <div class="install-progress"></div>
                    </button>
                `).join('') :
                `<button class="install-button ${program.installed ? 'success' : ''}" 
                         data-program="${program.name}"
                         data-variant="${program.defaultVariant || 'apt'}"
                         ${program.installed ? 'disabled' : ''}>
                    <i class="fas ${program.installed ? 'fa-check' : 'fa-download'}"></i>
                    <span class="button-text">
                        ${program.installed ? 'Installed' : `Install ${program.name}`}
                    </span>
                    <div class="install-progress"></div>
                 </button>`;

            card.innerHTML = `
                <div class="program-header">
                    <img src="${program.logo}" alt="${program.name} logo" class="program-logo">
                    <div class="program-badges">
                        <span class="program-category">${program.category}</span>
                        ${program.isCustomized ? '<span class="custom-badge">Custom Patch</span>' : ''}
                    </div>
                </div>
                <div class="program-info">
                    <h2>${program.name}</h2>
                    <p class="program-description">${program.description}</p>
                    ${program.customDescription ? `<p class="custom-description">${program.customDescription}</p>` : ''}
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
                const btn = e.currentTarget;
                const programName = btn.dataset.program;
                const variant = btn.dataset.variant;
                
                btn.disabled = true;
                btn.classList.add('installing');
                btn.querySelector('.button-text').textContent = 'Installing...';
                
                try {
                    const result = await window.pywebview.api.install_program(programName, variant);
                    if (result.success) {
                        btn.classList.remove('installing');
                        btn.classList.add('success');
                        btn.querySelector('.button-text').textContent = 'Installed';
                        btn.querySelector('i').className = 'fas fa-check';
                    } else {
                        btn.classList.remove('installing');
                        btn.classList.add('error');
                        btn.querySelector('.button-text').textContent = 'Error';
                        btn.querySelector('i').className = 'fas fa-exclamation-triangle';
                        showError(result.message);
                    }
                } catch (error) {
                    btn.classList.remove('installing');
                    btn.classList.add('error');
                    btn.querySelector('.button-text').textContent = 'Error';
                    btn.querySelector('i').className = 'fas fa-exclamation-triangle';
                    showError('Installation failed');
                }
            });
        });
    }

    function showError(message) {
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
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