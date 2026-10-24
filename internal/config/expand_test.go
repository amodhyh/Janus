package config

import "testing"

func TestExpandVar(t *testing.T) {
	t.Setenv("JANUS_T_SET", "x")
	t.Setenv("JANUS_T_EMPTY", "")
	cases := map[string]string{
		"JANUS_T_SET":                "x",
		"JANUS_T_SET:-d":             "x",
		"JANUS_T_EMPTY:-d":           "d",
		"JANUS_T_UNSET:-localhost:1": "localhost:1",
		"JANUS_T_UNSET":              "",
	}
	for ref, want := range cases {
		if got := expandVar(ref); got != want {
			t.Errorf("expandVar(%q) = %q, want %q", ref, got, want)
		}
	}
}
