document.addEventListener('DOMContentLoaded', function() {
    // =====================
    // Helper: Toggle visibility
    // =====================
    var toggleButtons = document.getElementsByClassName('toggle-password');
    for (var i = 0; i < toggleButtons.length; i++) {
        (function(btn) {
            var input = document.getElementById(btn.dataset.target);
            btn.onclick = function() {
                if (input.type === 'password') {
                    input.type = 'text';
                    btn.textContent = '🙈';
                } else {
                    input.type = 'password';
                    btn.textContent = '👁️';
                }
            };
        })(toggleButtons[i]);
    }

    // =====================
    // Password validation helper
    // =====================
    function updateRequirements(input, reqItems) {
        var pwd = input.value;
        var validations = {
            length: pwd.length >= 8,
            letter: /[a-zA-Z]/.test(pwd),
            number: /\d/.test(pwd),
            special: /[!@#$%^&*()_+\-=\[\]{};:'",.<>?/\\|`~]/.test(pwd)
        };

        for (var key in validations) {
            if (reqItems[key]) {
                reqItems[key].textContent = (validations[key] ? '✓' : '✗') + ' ' + reqItems[key].dataset.text;
                reqItems[key].className = validations[key] ? 'valid' : '';
            }
        }

        // Return true if all validations pass
        return Object.values(validations).every(Boolean);
    }

    // =====================
    // Change Password Section
    // =====================
    var newPasswordInput = document.getElementById('new_password');
    var confirmPasswordInput = document.getElementById('confirm_password');
    var submitBtn = document.getElementById('submit-btn');
    var matchMessage = document.getElementById('password-match-message');

    var requirements = {
        length: document.getElementById('req-length'),
        letter: document.getElementById('req-letter'),
        number: document.getElementById('req-number'),
        special: document.getElementById('req-special')
    };

    // Store original text for reuse
    for (var key in requirements) {
        if (requirements[key]) requirements[key].dataset.text = requirements[key].textContent.slice(2);
    }

    function checkPasswordMatch() {
        if (!matchMessage) return;

        if (confirmPasswordInput.value === '') {
            matchMessage.textContent = '';
            matchMessage.className = 'match-message';
            submitBtn.disabled = false;
            return;
        }

        if (newPasswordInput.value === confirmPasswordInput.value) {
            matchMessage.textContent = '✓ Passwords match';
            matchMessage.className = 'match-message success';
            submitBtn.disabled = false;
        } else {
            matchMessage.textContent = '✗ Passwords do not match';
            matchMessage.className = 'match-message error';
            submitBtn.disabled = true;
        }
    }

    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            updateRequirements(this, requirements);
            checkPasswordMatch();
        });
    }

    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', checkPasswordMatch);
    }

    var changeForm = document.getElementById('change-password-form');
    if (changeForm) {
        changeForm.addEventListener('submit', function(e) {
            var allValid = updateRequirements(newPasswordInput, requirements);
            if (newPasswordInput.value !== confirmPasswordInput.value) {
                e.preventDefault();
                alert('Passwords do not match');
            } else if (!allValid) {
                e.preventDefault();
                alert('Please meet all password requirements');
            }
        });
    }

    // =====================
    // Register Section
    // =====================
    var registerPasswordInput = document.getElementById('register_password');
    var registerRequirementsBox = document.getElementById('register-password-requirements');

    var reqItems = {
        length: document.getElementById('reg-req-length'),
        letter: document.getElementById('reg-req-letter'),
        number: document.getElementById('reg-req-number'),
        special: document.getElementById('reg-req-special')
    };

    // Store original text for reuse
    for (var key in reqItems) {
        if (reqItems[key]) reqItems[key].dataset.text = reqItems[key].textContent.slice(2);
    }

    if (registerPasswordInput && registerRequirementsBox) {
        registerPasswordInput.addEventListener('focus', () => registerRequirementsBox.classList.add('show'));
        registerPasswordInput.addEventListener('blur', () => setTimeout(() => registerRequirementsBox.classList.remove('show'), 200));

        registerPasswordInput.addEventListener('input', function() {
            updateRequirements(this, reqItems);
        });

        var registerForm = document.getElementById('register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', function(e) {
                var allValid = updateRequirements(registerPasswordInput, reqItems);
                if (!allValid) {
                    e.preventDefault();
                    alert('Password does not meet all requirements.');
                    registerPasswordInput.focus();
                }
            });
        }
    }
    
    function deleteAdmin(btn) {
        alert('Are you sure you want to delete this admin?');
        btn.closest('form').submit(); 
}

});
