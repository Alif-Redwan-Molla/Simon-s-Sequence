#version 330

in vec3 in_position;
in vec3 in_normal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat3 normal_matrix;

out vec3 v_normal;
out vec3 v_frag_pos;

void main() {
    vec4 world_pos = model * vec4(in_position, 1.0);
    v_frag_pos = world_pos.xyz;
    v_normal = normalize(normal_matrix * in_normal);
    gl_Position = projection * view * world_pos;
}
