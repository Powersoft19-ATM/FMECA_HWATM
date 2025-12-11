let URL;
let baseURL;
console.log(process.env.NODE_ENV);
if (process.env.NODE_ENV === "development") {
  URL = "http://localhost:8000";
} else if (process.env.NODE_ENV === "production") {
  URL = window.location.href;
} else {
  URL = window.location.href;
}
export { URL, baseURL };
