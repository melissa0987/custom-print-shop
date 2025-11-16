function sendRequest(url, method, body, successMsg) {
    fetch(url, {
        method: method,
        headers: {"Content-Type": "application/json"},
        body: body ? JSON.stringify(body) : null
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert("Error: " + data.error);
        } else {
            alert(successMsg);
            location.reload();
        }
    })
    .catch(err => alert("Failed: " + err));
}


// UPDATE ADMIN
document.getElementById("saveAdminBtn").addEventListener("click", () => {
    const adminId = document.getElementById("adminId").value;

    const body = {
        email: document.getElementById("emailField").value,
        first_name: document.getElementById("firstNameField").value,
        last_name: document.getElementById("lastNameField").value,
        role: document.getElementById("roleField").value,
        is_active: document.getElementById("statusField").value === "true"
    };

    sendRequest(`/admin/admins/${adminId}`, "PUT", body, "Admin updated");
});


// CHANGE PASSWORD
document.getElementById("changePasswordBtn").addEventListener("click", () => {
    const adminId = document.getElementById("adminId").value;
    const pwd = document.getElementById("passwordField").value;

    if (!pwd) return alert("Enter a password");

    sendRequest(`/admin/admins/${adminId}/password`, "PUT", { password: pwd }, "Password changed");
});


// ACTIVATE
const activateBtn = document.getElementById("activateBtn");
if (activateBtn) {
    activateBtn.addEventListener("click", () => {
        const adminId = document.getElementById("adminId").value;
        sendRequest(`/admin/admins/${adminId}/activate`, "PUT", null, "Admin activated");
    });
}


// DEACTIVATE
const deactivateBtn = document.getElementById("deactivateBtn");
if (deactivateBtn) {
    deactivateBtn.addEventListener("click", () => {
        const adminId = document.getElementById("adminId").value;
        sendRequest(`/admin/admins/${adminId}/deactivate`, "PUT", null, "Admin deactivated");
    });
}


// DELETE
const deleteBtn = document.getElementById("deleteBtn");
if (deleteBtn) {
    deleteBtn.addEventListener("click", () => {
        const adminId = document.getElementById("adminId").value;

        if (!confirm("Are you sure? This cannot be undone.")) return;

        fetch(`/admin/admins/${adminId}`, { method: "DELETE" })
        .then(res => res.json())
        .then(data => {
            if (data.error) alert("Error: " + data.error);
            else {
                alert("Admin deleted");
                window.location.href = "/admin/admins";
            }
        });
    });
}
