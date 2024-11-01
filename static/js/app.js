// Form validation functions
function validateDateRange(startTime, endTime) {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const now = new Date();
    
    // Remove minutes and seconds for today comparison
    now.setMinutes(0, 0, 0);
    
    if (start < now) {
        return { valid: false, message: 'Start time cannot be in the past' };
    }
    
    if (end <= start) {
        return { valid: false, message: 'End time must be after start time' };
    }
    
    // Check if booking is within allowed hours (e.g., 8 AM to 10 PM)
    const startHour = start.getHours();
    const endHour = end.getHours();
    
    if (startHour < 8 || endHour > 22) {
        return { valid: false, message: 'Bookings are only allowed between 8 AM and 10 PM' };
    }
    
    // Check if duration is not more than 4 hours
    const duration = (end - start) / (1000 * 60 * 60); // duration in hours
    if (duration > 4) {
        return { valid: false, message: 'Bookings cannot exceed 4 hours' };
    }
    
    return { valid: true };
}

// Initialize date pickers when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Flatpickr for datetime inputs
    const commonConfig = {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        minTime: "08:00",
        maxTime: "22:00",
        minuteIncrement: 30,
        time_24hr: true
    };

    // Start time picker
    const startPicker = flatpickr("#start_time", {
        ...commonConfig,
        minDate: "today",
        onChange: function(selectedDates, dateStr) {
            // Update end time minimum date when start time changes
            if (selectedDates[0]) {
                endPicker.set('minDate', selectedDates[0]);
            }
        }
    });

    // End time picker
    const endPicker = flatpickr("#end_time", {
        ...commonConfig,
        minDate: "today"
    });

    // Form validation
    const bookingForm = document.getElementById('bookingForm');
    if (bookingForm) {
        bookingForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const startTime = document.getElementById('start_time').value;
            const endTime = document.getElementById('end_time').value;
            
            const validation = validateDateRange(startTime, endTime);
            
            if (!validation.valid) {
                showError(validation.message);
                return;
            }
            
            this.submit();
        });
    }
});

// Admin form validation
const addTenantForm = document.getElementById('addTenantForm');
if (addTenantForm) {
    addTenantForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const building = document.getElementById('building').value;
        const apartment = document.getElementById('apartment').value;
        
        if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
            showError('Please enter a valid email address');
            return;
        }
        
        if (building.trim() === '' || apartment.trim() === '') {
            showError('Building and apartment are required');
            return;
        }
        
        this.submit();
    });
}

// Error display function
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
    errorDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const form = document.querySelector('form');
    form.insertBefore(errorDiv, form.firstChild);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
} 