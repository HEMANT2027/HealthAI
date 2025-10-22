export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID 

export const GOOGLE_CONFIG = {
  client_id: GOOGLE_CLIENT_ID,
  auto_select: false,
  cancel_on_tap_outside: true,
};

// Button configuration
export const GOOGLE_BUTTON_CONFIG = {
  theme: "outline",
  size: "large",
  text: "continue_with",
  shape: "rectangular",
  width: "250px",
  height: "48px",
}; 