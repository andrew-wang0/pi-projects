import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#6f4e37",
      dark: "#5a3f2d",
      light: "#8a664b",
      contrastText: "#fffaf3",
    },
    secondary: {
      main: "#c9a67f",
      dark: "#ac875f",
      light: "#dec2a2",
      contrastText: "#2f1f14",
    },
    background: {
      default: "#f4e6d2",
      paper: "#faefdf",
    },
    text: {
      primary: "#3f2b1d",
      secondary: "#6b5240",
    },
  },
  typography: {
    fontFamily: 'var(--font-geist-sans), "Trebuchet MS", "Avenir Next", sans-serif',
    button: {
      textTransform: "none",
      fontWeight: 700,
    },
  },
  components: {
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundImage: "none",
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        fullWidth: true,
      },
    },
  },
});

export default theme;
