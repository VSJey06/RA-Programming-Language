package com.ra.lang;

import android.os.Bundle;
import android.text.SpannableStringBuilder;
import android.text.method.ScrollingMovementMethod;
import android.view.KeyEvent;
import android.view.inputmethod.EditorInfo;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends AppCompatActivity {

    private TextView textOutput;
    private ScrollView scrollOutput;
    private EditText editInput;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        textOutput = findViewById(R.id.textOutput);
        scrollOutput = findViewById(R.id.scrollOutput);
        editInput = findViewById(R.id.editInput);

        textOutput.setMovementMethod(new ScrollingMovementMethod());

        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }

        editInput.requestFocus();
        editInput.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEND ||
                    (event != null && event.getAction() == KeyEvent.ACTION_DOWN &&
                     event.getKeyCode() == KeyEvent.KEYCODE_ENTER)) {
                String input = v.getText().toString();
                if (input.length() > 0) {
                    execute(input);
                    v.setText("");
                }
                return true;
            }
            return false;
        });
    }

    private void execute(String input) {
        appendOutput("RA > " + input);
        try {
            Python py = Python.getInstance();
            String result = py.getModule("ra_bridge").callAttr("exec", input).toString();
            if (result.length() > 0) {
                appendOutput(result);
            }
        } catch (Exception e) {
            appendOutput("Error: " + e.getMessage());
        }
    }

    private void appendOutput(String text) {
        SpannableStringBuilder sb = new SpannableStringBuilder(textOutput.getText());
        if (sb.length() > 0) {
            sb.append("\n");
        }
        sb.append(text);
        textOutput.setText(sb);
        scrollOutput.post(() -> scrollOutput.fullScroll(ScrollView.FOCUS_DOWN));
    }
}
