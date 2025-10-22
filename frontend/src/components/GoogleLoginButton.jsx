import { useEffect, useRef } from 'react';
// import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
// import { googleLogin } from '../store/authSlice.js';
import { GOOGLE_CONFIG, GOOGLE_BUTTON_CONFIG } from '../config/google.js';

function GoogleLoginButton() {
  // const dispatch = useDispatch();
  const navigate = useNavigate();
  const googleSignInRef = useRef(null);

  useEffect(() => {
    // Load Google Identity Services script
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = initializeGoogleSignIn;
    document.head.appendChild(script);

    return () => {
      // Cleanup script when component unmounts
      const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
      if (existingScript) {
        document.head.removeChild(existingScript);
      }
    };
  }, []);

  const initializeGoogleSignIn = () => {
    if (window.google && googleSignInRef.current) {
      window.google.accounts.id.initialize({
        ...GOOGLE_CONFIG,
        callback: handleCallbackResponse,
      });

      window.google.accounts.id.renderButton(googleSignInRef.current, GOOGLE_BUTTON_CONFIG);
    }
  };

  const handleCallbackResponse = async (response) => {
    // try {
    //   const googleToken = response.credential;
      
    //   const result = await dispatch(googleLogin(googleToken));
      
    //   if (googleLogin.fulfilled.match(result)) {
    //     if (result.payload.success) {
    //       // Navigate to dashboard
    //       navigate('/dashboard');
    //     } else {
    //       console.error('Google login failed:', result.payload.message);
    //       alert('Google login failed. Please try again.');
    //     }
    //   } else {
    //     console.error('Google login error:', result.error);
    //     alert('An error occurred during Google login. Please try again.');
    //   }
    // } catch (error) {
    //   console.error('Google login error:', error);
    //   alert('An error occurred during Google login. Please try again.');
    // }
  };

  return (
    <div 
      ref={googleSignInRef}
      className="w-full flex justify-center"
    />
  );
}

export default GoogleLoginButton; 