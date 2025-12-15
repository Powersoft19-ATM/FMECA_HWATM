let URL;
let baseURL;
console.log(process.env.NODE_ENV);
if (process.env.NODE_ENV === "development") {
  URL = "https://fmeca-hwatm.onrender.com";
} else if (process.env.NODE_ENV === "production") {
  URL = "https://fmeca-hwatm.onrender.com";
} else {
  URL = "https://fmeca-hwatm.onrender.com";
}
export { URL, baseURL };
