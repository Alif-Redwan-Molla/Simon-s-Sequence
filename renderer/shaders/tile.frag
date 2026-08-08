#version 330

in vec3 v_normal;
in vec3 v_frag_pos;
out vec4 f_color;

uniform vec3 base_color;
uniform vec3 light_dir;     // direction the light travels, e.g. (-0.4, -1.0, -0.3)
uniform vec3 view_pos;
uniform float emissive;     // 0..1, brightens the tile for flash/press feedback

void main() {
    vec3 N = normalize(v_normal);
    vec3 L = normalize(-light_dir);
    vec3 V = normalize(view_pos - v_frag_pos);
    vec3 H = normalize(L + V);

    float diff = max(dot(N, L), 0.0);
    float spec = pow(max(dot(N, H), 0.0), 40.0);

    vec3 ambient = 0.32 * base_color;
    vec3 diffuse = diff * base_color * 0.75;
    vec3 specular = vec3(0.55) * spec;

    vec3 color = ambient + diffuse + specular + base_color * emissive;
    f_color = vec4(color, 1.0);
}
