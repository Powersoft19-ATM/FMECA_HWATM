import React, { useState } from "react";
import axios from "axios";
import { URL } from "../../config";
function UserProfile({ user, onBack, onLogout }) {
  const [isEditing, setIsEditing] = useState(false);
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setMessage("");
    setError("");
    setLoading(true);

    try {
      const response = await axios.put(`${URL}/users/${user.username}`, {
        full_name: fullName,
        email: email,
      });

      setMessage("Profile updated successfully!");
      setIsEditing(false);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setMessage("");
    setError("");

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }

    if (newPassword.length < 6) {
      setError("Password must be at least 6 characters long");
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(`${URL}/change-password`, {
        current_password: currentPassword,
        new_password: newPassword,
      });

      setMessage("Password changed successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to change password");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + " " + date.toLocaleTimeString();
  };

  return (
    <div className="profile-container">
      <div className="profile-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Dashboard
        </button>
        <h2 className="profile-title">User Profile</h2>
      </div>

      <div className="profile-content">
        <div className="profile-info">
          <h3>Account Information</h3>

          {message && <div className="success-message">{message}</div>}
          {error && <div className="error-message">{error}</div>}

          <div className="info-grid">
            <div className="info-item">
              <label>Username</label>
              <div className="info-value">{user?.username}</div>
            </div>

            <div className="info-item">
              <label>Role</label>
              <div className="info-value">
                <span className={`role-badge role-${user?.role}`}>
                  {user?.role}
                </span>
              </div>
            </div>

            <div className="info-item">
              <label>Account Created</label>
              <div className="info-value">{formatDate(user?.created_at)}</div>
            </div>

            <div className="info-item">
              <label>Last Updated</label>
              <div className="info-value">{formatDate(user?.updated_at)}</div>
            </div>

            {user?.last_login && (
              <div className="info-item">
                <label>Last Login</label>
                <div className="info-value">{formatDate(user?.last_login)}</div>
              </div>
            )}
          </div>

          {isEditing ? (
            <form onSubmit={handleUpdateProfile} className="profile-form">
              <div className="form-group">
                <label htmlFor="fullName">Full Name</label>
                <input
                  type="text"
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Enter full name"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter email"
                  required
                />
              </div>

              <div className="form-buttons">
                <button
                  type="submit"
                  className="save-button"
                  disabled={loading}
                >
                  {loading ? "Saving..." : "Save Changes"}
                </button>
                <button
                  type="button"
                  className="cancel-button"
                  onClick={() => setIsEditing(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="static-info">
              <div className="info-item">
                <label>Full Name</label>
                <div className="info-value">{user?.full_name || "Not set"}</div>
              </div>

              <div className="info-item">
                <label>Email</label>
                <div className="info-value">{user?.email || "Not set"}</div>
              </div>

              <button
                className="edit-button"
                onClick={() => setIsEditing(true)}
              >
                Edit Profile
              </button>
            </div>
          )}
        </div>

        <div className="password-section">
          <h3>Change Password</h3>
          <form onSubmit={handleChangePassword} className="password-form">
            <div className="form-group">
              <label htmlFor="currentPassword">Current Password</label>
              <input
                type="password"
                id="currentPassword"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="newPassword">New Password</label>
              <input
                type="password"
                id="newPassword"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm New Password</label>
              <input
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                required
              />
            </div>

            <button
              type="submit"
              className="change-password-button"
              disabled={loading}
            >
              {loading ? "Changing..." : "Change Password"}
            </button>
          </form>
        </div>

        <div className="account-actions">
          <h3>Account Actions</h3>
          <div className="action-buttons">
            <button className="logout-profile-button" onClick={onLogout}>
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UserProfile;
