// Add this in config or main.js
const ADMINS = ["94766359869", "94784548818"];

function isAdmin(phone) {
  return ADMINS.includes(phone);
}
