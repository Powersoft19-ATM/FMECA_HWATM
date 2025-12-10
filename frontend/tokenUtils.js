export const checkTokenExpiration = () => {
  const token = localStorage.getItem("access_token");
  if (!token) return false;

  try {
    // Simple check - if token exists and not too old
    const tokenAge =
      Date.now() - (localStorage.getItem("token_timestamp") || 0);
    // Token expires after 30 minutes (30 * 60 * 1000 = 1,800,000 ms)
    const maxAge = 30 * 60 * 1000;

    if (tokenAge > maxAge) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("username");
      localStorage.removeItem("token_timestamp");
      return false;
    }
    return true;
  } catch (error) {
    console.error("Error checking token:", error);
    return false;
  }
};

export const saveTokenTimestamp = () => {
  localStorage.setItem("token_timestamp", Date.now());
};

export const clearAuthData = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("username");
  localStorage.removeItem("token_timestamp");
  localStorage.removeItem("user_details");
};
