document.addEventListener('DOMContentLoaded', async () => {
    const programsContainer = document.getElementById('programs-container');
    const navLinks = document.querySelectorAll('nav a');
    const searchInput = document.getElementById('program-search');
    let currentPrograms = [];
    let currentCategory = 'image_editing';

    async function loadPrograms(category = 'image_editing') {
        currentCategory = category;
        const programs = await window.pywebview.api.get_programs();
        currentPrograms = programs[category];
        renderPrograms(currentPrograms);
    }

    function renderPrograms(programs) {
        programsContainer.innerHTML = '';
        
        if (programs.length === 0) {
            programsContainer.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <p>No programs found matching your search</p>
                </div>
            `;
            return;
        }

        programs.forEach(program => {
            const card = document.createElement('div');
            card.className = 'program-card';
            
            const logoPath = program.logo || '/static/img/logos/default.png';
            
            card.innerHTML = `
                <div class="program-header">
                    <img src="${logoPath}" alt="${program.name} logo" class="program-logo">
                    <div class="program-info">
                        <h2>${program.name}</h2>
                        <div class="program-badges">
                            <span class="program-category">${program.category}</span>
                            ${program.isCustomized ? '<span class="custom-badge">Custom Version Available</span>' : ''}
                        </div>
                    </div>
                </div>
                <p class="program-description">${program.description}</p>
                ${program.isCustomized ? `
                    <p class="custom-description">
                        <i class="fas fa-magic"></i> ${program.customDescription}
                    </p>
                ` : ''}
                <div class="program-variants">
                    ${renderVariants(program)}
                </div>
            `;
            
            programsContainer.appendChild(card);
        });

        // Add install button listeners
        document.querySelectorAll('.install-button').forEach(button => {
            button.addEventListener('click', async (e) => {
                const btn = e.currentTarget;
                const program = btn.dataset.program;
                const variant = btn.dataset.variant;
                
                btn.classList.add('installing');
                btn.disabled = true;
                
                try {
                    const result = await window.pywebview.api.install_program(program, variant);
                    if (result.success) {
                        btn.classList.remove('installing');
                        btn.classList.add('success');
                        btn.innerHTML = `
                            <i class="fas fa-check"></i>
                            <span class="button-text">Installed</span>
                        `;
                    } else {
                        throw new Error(result.message);
                    }
                } catch (error) {
                    btn.classList.remove('installing');
                    btn.classList.add('error');
                    btn.disabled = false;
                    showError(`Failed to install ${program}: ${error.message}`);
                }
            });
        });
    }

    function renderVariants(program) {
        if (!program.variants) {
            return `
                <button class="install-button ${program.installed ? 'success' : ''}" 
                        data-program="${program.name}"
                        data-variant="apt"
                        ${program.installed ? 'disabled' : ''}>
                    <i class="fas ${program.installed ? 'fa-check' : 'fa-download'}"></i>
                    <span class="button-text">
                        ${program.installed ? 'Installed' : `Install ${program.name}`}
                    </span>
                    <div class="install-progress"></div>
                </button>
            `;
        }

        return program.variants.map(variant => `
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
        `).join('');
    }

    function filterPrograms(searchTerm) {
        const filtered = currentPrograms.filter(program => 
            program.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            program.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
            program.category.toLowerCase().includes(searchTerm.toLowerCase())
        );
        renderPrograms(filtered);
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

    searchInput.addEventListener('input', (e) => {
        filterPrograms(e.target.value);
    });

    // Navigation event listeners
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const category = e.target.closest('a').dataset.category;
            loadPrograms(category);
            
            navLinks.forEach(l => l.classList.remove('active'));
            e.target.closest('a').classList.add('active');
            
            searchInput.value = '';
        });
    });

    // Load initial programs
    loadPrograms();
});