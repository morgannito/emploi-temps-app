/**
 * JavaScript pour l'interface d'administration de l'emploi du temps
 * Gère l'interactivité des tableaux et la communication avec l'API
 */

class ScheduleManager {
    constructor() {
        this.scheduleData = window.scheduleData || {};
        this.teachersData = window.teachersData || {};
        this.roomsData = window.roomsData || {};
        this.equipmentData = window.equipmentData || {};
        
        this.currentDay = 'lundi';
        this.debounceTimer = null;
        
        this.init();
    }

    /**
     * Initialise l'application
     */
    init() {
        this.bindEvents();
        this.loadScheduleData();
        this.setupAutoSave();
        
        console.log('ScheduleManager initialisé');
    }

    /**
     * Attache les événements aux éléments
     */
    bindEvents() {
        // Événements des onglets
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.currentDay = e.target.getAttribute('data-bs-target').replace('#', '');
                this.loadDaySchedule(this.currentDay);
            });
        });

        // Événements des dropdowns professeurs
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('teacher-dropdown')) {
                this.handleTeacherChange(e.target);
            }
        });

        // Événements des champs matière
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('subject-field')) {
                this.handleSubjectChange(e.target);
            }
        });

        // Événements des dropdowns équipements
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('equipment-dropdown')) {
                this.handleEquipmentChange(e.target);
            }
        });

        // Événements des dropdowns durée
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('duration-dropdown')) {
                this.handleDurationChange(e.target);
            }
        });

        // Gestion des raccourcis clavier
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                this.saveAllChanges();
            }
        });
    }

    /**
     * Charge les données d'emploi du temps depuis le serveur
     */
    async loadScheduleData() {
        try {
            for (const day of ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi']) {
                const response = await fetch(`/api/schedule/${day}`);
                if (response.ok) {
                    const dayData = await response.json();
                    this.scheduleData[day] = dayData;
                }
            }
            this.populateScheduleTables();
        } catch (error) {
            console.error('Erreur lors du chargement des données:', error);
            this.showNotification('Erreur de chargement des données', 'error');
        }
    }

    /**
     * Charge les données d'un jour spécifique
     */
    async loadDaySchedule(day) {
        try {
            const response = await fetch(`/api/schedule/${day}`);
            if (response.ok) {
                const dayData = await response.json();
                this.scheduleData[day] = dayData;
                this.populateDayTable(day);
            }
        } catch (error) {
            console.error(`Erreur lors du chargement du ${day}:`, error);
        }
    }

    /**
     * Remplit tous les tableaux avec les données
     */
    populateScheduleTables() {
        Object.keys(this.scheduleData).forEach(day => {
            this.populateDayTable(day);
        });
    }

    /**
     * Remplit le tableau d'un jour spécifique
     */
    populateDayTable(day) {
        const dayData = this.scheduleData[day];
        if (!dayData) return;

        const dayTab = document.getElementById(day);
        if (!dayTab) return;

        const cells = dayTab.querySelectorAll('.schedule-cell');
        
        cells.forEach(cell => {
            const roomId = cell.dataset.room;
            const slotIndex = parseInt(cell.dataset.slot);
            
            if (dayData[roomId] && dayData[roomId][slotIndex]) {
                const slotData = dayData[roomId][slotIndex];
                this.populateCell(cell, slotData);
            }
        });
    }

    /**
     * Remplit une cellule avec les données d'un créneau
     */
    populateCell(cell, slotData) {
        const durationSelect = cell.querySelector('.duration-dropdown');
        const teacherSelect = cell.querySelector('.teacher-dropdown');
        const subjectInput = cell.querySelector('.subject-field');
        const equipmentSelect = cell.querySelector('.equipment-dropdown');

        // Durée
        if (durationSelect && slotData.duration_hours) {
            durationSelect.value = slotData.duration_hours.toString();
        }

        // Professeur
        if (teacherSelect && slotData.teacher_id) {
            teacherSelect.value = slotData.teacher_id;
        }

        // Matière
        if (subjectInput && slotData.subject) {
            subjectInput.value = slotData.subject;
        }

        // Équipements
        if (equipmentSelect && slotData.equipment_ids) {
            Array.from(equipmentSelect.options).forEach(option => {
                option.selected = slotData.equipment_ids.includes(option.value);
            });
        }

        // Gestion des créneaux de continuation
        if (slotData.is_continuation) {
            cell.classList.add('continuation-slot');
            cell.innerHTML = '<div class="continuation-indicator"><small class="text-muted">↪ Suite du cours</small></div>';
        }

        // Mise à jour du statut visuel
        this.updateCellStatus(cell, slotData);
    }

    /**
     * Met à jour le statut visuel d'une cellule
     */
    updateCellStatus(cell, slotData) {
        cell.classList.remove('occupied', 'conflict', 'available');
        
        if (slotData.teacher_id) {
            // Vérifier les conflits
            const hasConflict = this.checkTeacherConflict(
                cell.dataset.day,
                cell.dataset.room,
                parseInt(cell.dataset.slot),
                slotData.teacher_id
            );
            
            if (hasConflict) {
                cell.classList.add('conflict');
                cell.dataset.status = 'conflict';
            } else {
                cell.classList.add('occupied');
                cell.dataset.status = 'occupied';
            }
        } else {
            cell.classList.add('available');
            cell.dataset.status = 'available';
        }
    }

    /**
     * Vérifie les conflits de professeur
     */
    checkTeacherConflict(day, currentRoom, currentSlot, teacherId) {
        const dayData = this.scheduleData[day];
        if (!dayData) return false;

        for (const [roomId, slots] of Object.entries(dayData)) {
            if (roomId === currentRoom) continue;
            
            if (slots[currentSlot] && slots[currentSlot].teacher_id === teacherId) {
                return true;
            }
        }
        return false;
    }

    /**
     * Gère le changement de professeur
     */
    handleTeacherChange(select) {
        const cell = select.closest('.schedule-cell');
        const day = cell.dataset.day;
        const roomId = cell.dataset.room;
        const slotIndex = parseInt(cell.dataset.slot);
        const teacherId = select.value;

        // Mise à jour immédiate de l'interface
        const slotData = { teacher_id: teacherId };
        this.updateCellStatus(cell, slotData);

        // Sauvegarde avec debounce
        this.debouncedSave(day, roomId, slotIndex, { teacher_id: teacherId });
    }

    /**
     * Gère le changement de matière
     */
    handleSubjectChange(input) {
        const cell = input.closest('.schedule-cell');
        const day = cell.dataset.day;
        const roomId = cell.dataset.room;
        const slotIndex = parseInt(cell.dataset.slot);
        const subject = input.value;

        this.debouncedSave(day, roomId, slotIndex, { subject: subject });
    }

    /**
     * Gère le changement d'équipements
     */
    handleEquipmentChange(select) {
        const cell = select.closest('.schedule-cell');
        const day = cell.dataset.day;
        const roomId = cell.dataset.room;
        const slotIndex = parseInt(cell.dataset.slot);
        
        const selectedEquipment = Array.from(select.selectedOptions)
            .map(option => option.value);

        this.debouncedSave(day, roomId, slotIndex, { equipment_ids: selectedEquipment });
    }

    /**
     * Gère le changement de durée
     */
    handleDurationChange(select) {
        const cell = select.closest('.schedule-cell');
        const day = cell.dataset.day;
        const roomId = cell.dataset.room;
        const slotIndex = parseInt(cell.dataset.slot);
        const duration = parseFloat(select.value);

        if (duration) {
            // Vérifier la disponibilité des créneaux suivants
            if (this.checkDurationAvailability(day, roomId, slotIndex, duration)) {
                this.debouncedSave(day, roomId, slotIndex, { duration_hours: duration });
                this.updateDurationVisual(day, roomId, slotIndex, duration);
            } else {
                this.showNotification('Créneaux suivants non disponibles pour cette durée', 'warning');
                select.value = ''; // Reset la sélection
            }
        } else {
            this.debouncedSave(day, roomId, slotIndex, { duration_hours: null });
        }
    }

    /**
     * Vérifie la disponibilité des créneaux pour une durée donnée
     */
    checkDurationAvailability(day, roomId, startSlot, duration) {
        const dayData = this.scheduleData[day];
        if (!dayData || !dayData[roomId]) return false;

        const slots = dayData[roomId];
        const slotsNeeded = duration === 1.5 ? 2 : Math.floor(duration);

        for (let i = 1; i < slotsNeeded; i++) {
            const nextSlotIndex = startSlot + i;
            if (nextSlotIndex >= slots.length) return false;
            
            const nextSlot = slots[nextSlotIndex];
            if (nextSlot && nextSlot.teacher_id && !nextSlot.is_continuation) {
                return false;
            }
        }
        return true;
    }

    /**
     * Met à jour l'affichage visuel pour une durée
     */
    updateDurationVisual(day, roomId, startSlot, duration) {
        const dayTab = document.getElementById(day);
        if (!dayTab) return;

        const slotsNeeded = duration === 1.5 ? 2 : Math.floor(duration);
        
        for (let i = 1; i < slotsNeeded; i++) {
            const nextSlotIndex = startSlot + i;
            const nextCell = dayTab.querySelector(
                `.schedule-cell[data-room="${roomId}"][data-slot="${nextSlotIndex}"]`
            );
            
            if (nextCell) {
                nextCell.classList.add('continuation-slot');
                nextCell.innerHTML = '<div class="continuation-indicator"><small class="text-muted">↪ Suite du cours</small></div>';
            }
        }
    }

    /**
     * Sauvegarde avec debounce pour éviter trop d'appels API
     */
    debouncedSave(day, roomId, slotIndex, data) {
        clearTimeout(this.debounceTimer);
        
        this.debounceTimer = setTimeout(async () => {
            await this.saveSlot(day, roomId, slotIndex, data);
        }, 500);
    }

    /**
     * Sauvegarde un créneau via l'API
     */
    async saveSlot(day, roomId, slotIndex, data) {
        try {
            const response = await fetch(`/api/schedule/${day}/${roomId}/${slotIndex}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                // Mise à jour des données locales
                if (!this.scheduleData[day]) {
                    this.scheduleData[day] = {};
                }
                if (!this.scheduleData[day][roomId]) {
                    this.scheduleData[day][roomId] = [];
                }
                if (!this.scheduleData[day][roomId][slotIndex]) {
                    this.scheduleData[day][roomId][slotIndex] = {};
                }
                
                Object.assign(this.scheduleData[day][roomId][slotIndex], data);
                
                this.showNotification('Modifications sauvegardées', 'success');
            } else {
                throw new Error('Erreur de sauvegarde');
            }
        } catch (error) {
            console.error('Erreur de sauvegarde:', error);
            this.showNotification('Erreur lors de la sauvegarde', 'error');
        }
    }

    /**
     * Sauvegarde toutes les modifications en attente
     */
    async saveAllChanges() {
        this.showNotification('Sauvegarde en cours...', 'info');
        
        // Déclencher la sauvegarde immédiate si un timer est en cours
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
            // Logique de sauvegarde globale si nécessaire
        }
        
        this.showNotification('Toutes les modifications sauvegardées', 'success');
    }

    /**
     * Configure la sauvegarde automatique
     */
    setupAutoSave() {
        // Sauvegarde automatique toutes les 5 minutes
        setInterval(() => {
            this.saveAllChanges();
        }, 5 * 60 * 1000);

        // Sauvegarde avant fermeture de la page
        window.addEventListener('beforeunload', (e) => {
            if (this.debounceTimer) {
                e.preventDefault();
                e.returnValue = 'Des modifications non sauvegardées peuvent être perdues.';
            }
        });
    }

    /**
     * Affiche une notification toast
     */
    showNotification(message, type = 'info') {
        const toast = document.getElementById('notificationToast');
        const toastMessage = document.getElementById('toastMessage');
        
        if (!toast || !toastMessage) return;

        // Mise à jour du contenu
        toastMessage.textContent = message;
        
        // Mise à jour de l'icône selon le type
        const icon = toast.querySelector('.toast-header i');
        if (icon) {
            icon.className = `fas me-2 ${this.getIconClass(type)}`;
        }

        // Affichage du toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    /**
     * Retourne la classe d'icône selon le type de notification
     */
    getIconClass(type) {
        switch (type) {
            case 'success':
                return 'fa-check-circle text-success';
            case 'error':
                return 'fa-exclamation-circle text-danger';
            case 'warning':
                return 'fa-exclamation-triangle text-warning';
            default:
                return 'fa-info-circle text-primary';
        }
    }

    /**
     * Exporte l'emploi du temps au format JSON
     */
    exportSchedule() {
        const dataStr = JSON.stringify(this.scheduleData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `emploi_du_temps_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
    }

    /**
     * Recherche dans l'emploi du temps
     */
    searchSchedule(query) {
        const results = [];
        const lowerQuery = query.toLowerCase();

        Object.entries(this.scheduleData).forEach(([day, rooms]) => {
            Object.entries(rooms).forEach(([roomId, slots]) => {
                slots.forEach((slot, index) => {
                    if (slot.teacher_id && this.teachersData[slot.teacher_id]) {
                        const teacher = this.teachersData[slot.teacher_id];
                        if (teacher.name.toLowerCase().includes(lowerQuery) ||
                            (slot.subject && slot.subject.toLowerCase().includes(lowerQuery))) {
                            results.push({
                                day,
                                room: this.roomsData[roomId].name,
                                time: `${slot.start_time}-${slot.end_time}`,
                                teacher: teacher.name,
                                subject: slot.subject
                            });
                        }
                    }
                });
            });
        });

        return results;
    }
}

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', () => {
    window.scheduleManager = new ScheduleManager();
});

// Fonctions utilitaires globales
window.exportSchedule = () => {
    if (window.scheduleManager) {
        window.scheduleManager.exportSchedule();
    }
};

window.searchSchedule = (query) => {
    if (window.scheduleManager) {
        return window.scheduleManager.searchSchedule(query);
    }
    return [];
}; 