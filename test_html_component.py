import streamlit as st
import streamlit.components.v1 as components

# Simple HTML with JavaScript to test if Streamlit can capture values
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Test HTML Component</title>
</head>
<body>
    <h1>Test HTML Component</h1>
    <p>This is a test of the components.html function.</p>
    
    <button onclick="sendValue()">Click me</button>
    
    <script>
        function sendValue() {
            // This should send a value back to Streamlit
            if (window.parent && window.parent.Streamlit) {
                window.parent.Streamlit.setComponentValue("button_clicked");
            } else {
                console.log("Streamlit object not found");
            }
        }
        
        // Send an initial value
        if (window.parent && window.parent.Streamlit) {
            window.parent.Streamlit.setComponentValue("component_loaded");
        }
    </script>
</body>
</html>
"""

st.title("Test HTML Component")
st.write("Testing if we can send values back to Streamlit from HTML component...")

# Display the HTML component
result = components.html(
    html_content,
    height=400
)

st.write(f"Result from HTML component: {result}")