import React, { useEffect, useState } from "react";

function SessionChecker() {
  const [showWarning, setShowWarning] = useState(false);
  const [timeLeft, setTimeLeft] = useState(30 * 60); // 30 minutes in seconds

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    // Set initial timestamp if not set
    if (!localStorage.getItem("login_timestamp")) {
      localStorage.setItem("login_timestamp", Date.now());
    }

    // Check session every minute
    const checkInterval = setInterval(() => {
      const loginTime = parseInt(
        localStorage.getItem("login_timestamp") || "0"
      );
      const currentTime = Date.now();
      const elapsedMinutes = (currentTime - loginTime) / (1000 * 60);

      if (elapsedMinutes > 25) {
        // Show warning 5 minutes before expiry
        setShowWarning(true);
        setTimeLeft(Math.max(0, Math.floor(30 - elapsedMinutes) * 60));
      }

      if (elapsedMinutes > 30) {
        // Expire after 30 minutes
        localStorage.removeItem("access_token");
        localStorage.removeItem("username");
        localStorage.removeItem("login_timestamp");
        window.location.href = "/";
      }
    }, 60000); // Check every minute

    return () => clearInterval(checkInterval);
  }, []);

  const handleExtendSession = () => {
    localStorage.setItem("login_timestamp", Date.now());
    setShowWarning(false);
  };

  const handleLogoutNow = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("login_timestamp");
    window.location.href = "/";
  };

  if (!showWarning) return null;

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;

  return (
    <div className="session-warning">
      <span>
        Your session will expire in {minutes}:
        {seconds.toString().padStart(2, "0")}
      </span>
      <button onClick={handleExtendSession}>Stay Logged In</button>
      <button onClick={handleLogoutNow}>Logout Now</button>
    </div>
  );
}

export default SessionChecker;
