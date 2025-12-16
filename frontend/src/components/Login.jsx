import React, { useState } from "react";
import axios from "axios";
import { URL } from "../../config";

function Login({ onLogin }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (isRegistering) {
        // Registration
        const response = await axios.post(`${URL}/register`, {
          username,
          password,
          email,
          full_name: fullName,
        });

        setSuccess("Registration successful! You can now login.");
        setIsRegistering(false);
        setUsername("");
        setPassword("");
        setEmail("");
        setFullName("");
      } else {
        // Login
        const formData = new FormData();
        formData.append("username", username);
        formData.append("password", password);

        const response = await axios.post(`${URL}/token`, formData);

        if (response.data.access_token) {
          localStorage.setItem("access_token", response.data.access_token);
          localStorage.setItem("username", username);
          onLogin(response.data.access_token, username);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred");
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1 className="login-title">FMECA-HWATM Integrations</h1>
        <p className="login-subtitle">
          {isRegistering
            ? "Create a new account"
            : "Please login to access the system"}
        </p>

        {error && <div className="login-error">{error}</div>}
        {success && <div className="login-success">{success}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          {isRegistering && (
            <>
              <div className="form-group">
                <label htmlFor="fullName">Full Name</label>
                <input
                  type="text"
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Enter your full name"
                  required
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  required
                  disabled={loading}
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              disabled={loading}
            />
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading
              ? isRegistering
                ? "Registering..."
                : "Logging in..."
              : isRegistering
              ? "Register"
              : "Login"}
          </button>

          <div className="login-switch">
            <button
              type="button"
              className="switch-button"
              onClick={() => {
                setIsRegistering(!isRegistering);
                setError("");
                setSuccess("");
              }}
            >
              {isRegistering
                ? "Already have an account? Login"
                : "Don't have an account? Register"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Login;
