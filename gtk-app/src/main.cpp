#include <gtk-2.0/gtk/gtk.h>
#include <cairo.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sys/stat.h>

#define EXT_DIR "/mnt/us/extensions/kindle-series-manager"
#define HTTPD_PIDFILE "/tmp/kindle_series_manager_httpd.pid"
#define TOGGLE_W 120
#define TOGGLE_H 40

static const char* find_banner_path() {
    static const char* paths[] = {
        EXT_DIR "/assets/banner.png",
        "./assets/banner.png",
        "../assets/banner.png",
        NULL
    };
    for (int i = 0; paths[i]; i++) {
        if (g_file_test(paths[i], G_FILE_TEST_EXISTS))
            return paths[i];
    }
    return NULL;
}

static gboolean is_web_running() {
    return g_file_test(HTTPD_PIDFILE, G_FILE_TEST_EXISTS);
}

static gboolean toggle_expose(GtkWidget *widget, GdkEventExpose *event, gpointer data) {
    (void)event;
    gboolean active = GPOINTER_TO_INT(g_object_get_data(G_OBJECT(widget), "active"));

    cairo_t *cr = gdk_cairo_create(widget->window);
    int w = widget->allocation.width;
    int h = widget->allocation.height;
    double r = h / 2.0;
    double knob_r = r - 4;

    // Track
    if (active) {
        cairo_set_source_rgb(cr, 0.1, 0.1, 0.1);
    } else {
        cairo_set_source_rgb(cr, 0.75, 0.75, 0.75);
    }
    cairo_arc(cr, r, r, r, G_PI * 0.5, G_PI * 1.5);
    cairo_arc(cr, w - r, r, r, G_PI * 1.5, G_PI * 0.5);
    cairo_close_path(cr);
    cairo_fill(cr);

    // Knob
    double knob_x = active ? (w - r) : r;
    cairo_set_source_rgb(cr, 1, 1, 1);
    cairo_arc(cr, knob_x, r, knob_r, 0, G_PI * 2);
    cairo_fill(cr);

    // Border on knob
    cairo_set_source_rgb(cr, 0.5, 0.5, 0.5);
    cairo_set_line_width(cr, 1);
    cairo_arc(cr, knob_x, r, knob_r, 0, G_PI * 2);
    cairo_stroke(cr);

    cairo_destroy(cr);
    return TRUE;
}

static gboolean toggle_clicked(GtkWidget *widget, GdkEventButton *event, gpointer label_widget) {
    (void)event;
    gboolean active = GPOINTER_TO_INT(g_object_get_data(G_OBJECT(widget), "active"));
    active = !active;
    g_object_set_data(G_OBJECT(widget), "active", GINT_TO_POINTER(active));

    if (active) {
        system("sh " EXT_DIR "/bin/webapp.sh &");
    } else {
        system("sh " EXT_DIR "/bin/stopweb.sh");
    }

    const char *text = active ? "Web UI:  ON" : "Web UI:  OFF";
    gtk_label_set_text(GTK_LABEL(label_widget), text);

    gtk_widget_queue_draw(widget);
    return TRUE;
}

static void on_exit_clicked(GtkWidget *widget, gpointer data) {
    (void)widget;
    (void)data;
    gtk_main_quit();
}

static void apply_theme() {
    gtk_rc_parse_string(
        "style \"app-default\" {\n"
        "  bg[NORMAL] = \"#ffffff\"\n"
        "  fg[NORMAL] = \"#1a1a1a\"\n"
        "  font_name = \"Sans 14\"\n"
        "}\n"
        "style \"app-button\" {\n"
        "  bg[NORMAL] = \"#1a1a1a\"\n"
        "  bg[PRELIGHT] = \"#333333\"\n"
        "  bg[ACTIVE] = \"#555555\"\n"
        "  fg[NORMAL] = \"#ffffff\"\n"
        "  fg[PRELIGHT] = \"#ffffff\"\n"
        "  fg[ACTIVE] = \"#ffffff\"\n"
        "  font_name = \"Sans Bold 14\"\n"
        "  GtkButton::inner-border = {16, 16, 8, 8}\n"
        "}\n"
        "style \"label-large\" {\n"
        "  font_name = \"Sans Bold 16\"\n"
        "}\n"
        "widget_class \"*\" style \"app-default\"\n"
        "widget_class \"*GtkButton*\" style \"app-button\"\n"
    );
}

static GtkWidget* create_toggle_row(const char *label_text, gboolean initial_state, GCallback toggle_cb) {
    GtkWidget *hbox = gtk_hbox_new(FALSE, 12);

    GtkWidget *label = gtk_label_new(initial_state ? 
        g_strdup_printf("%s  ON", label_text) : 
        g_strdup_printf("%s  OFF", label_text));
    gtk_misc_set_alignment(GTK_MISC(label), 0, 0.5);
    gtk_box_pack_start(GTK_BOX(hbox), label, TRUE, TRUE, 0);

    GtkWidget *toggle = gtk_drawing_area_new();
    gtk_widget_set_size_request(toggle, TOGGLE_W, TOGGLE_H);
    g_object_set_data(G_OBJECT(toggle), "active", GINT_TO_POINTER(initial_state));
    gtk_widget_add_events(toggle, GDK_BUTTON_PRESS_MASK);
    g_signal_connect(toggle, "expose-event", G_CALLBACK(toggle_expose), NULL);
    g_signal_connect(toggle, "button-press-event", G_CALLBACK(toggle_cb), label);
    gtk_box_pack_end(GTK_BOX(hbox), toggle, FALSE, FALSE, 0);

    return hbox;
}

int main(int argc, char* argv[]) {
    gtk_init(&argc, &argv);
    apply_theme();

    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window),
        "L:A_N:application_ID:org.mlapaglia.kindle-series-manager_PC:T");
    g_signal_connect(window, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *vbox = gtk_vbox_new(FALSE, 0);
    gtk_container_add(GTK_CONTAINER(window), vbox);

    // Banner
    const char *banner_path = find_banner_path();
    if (banner_path) {
        GtkWidget *banner = gtk_image_new_from_file(banner_path);
        gtk_box_pack_start(GTK_BOX(vbox), banner, FALSE, FALSE, 0);
    }

    // Content area with padding
    GtkWidget *content = gtk_vbox_new(FALSE, 16);
    GtkWidget *content_align = gtk_alignment_new(0, 0, 1, 0);
    gtk_alignment_set_padding(GTK_ALIGNMENT(content_align), 20, 20, 24, 24);
    gtk_container_add(GTK_CONTAINER(content_align), content);
    gtk_box_pack_start(GTK_BOX(vbox), content_align, TRUE, TRUE, 0);

    // Web UI toggle
    GtkWidget *web_row = create_toggle_row("Web UI:", is_web_running(), G_CALLBACK(toggle_clicked));
    gtk_box_pack_start(GTK_BOX(content), web_row, FALSE, FALSE, 0);

    // Separator
    GtkWidget *sep = gtk_hseparator_new();
    gtk_box_pack_start(GTK_BOX(content), sep, FALSE, FALSE, 0);

    // Exit button at bottom
    GtkWidget *exit_btn = gtk_button_new_with_label("Exit");
    gtk_widget_set_size_request(exit_btn, -1, 60);
    g_signal_connect(exit_btn, "clicked", G_CALLBACK(on_exit_clicked), NULL);

    GtkWidget *btn_align = gtk_alignment_new(0.5, 1.0, 0.4, 0);
    gtk_alignment_set_padding(GTK_ALIGNMENT(btn_align), 0, 20, 0, 0);
    gtk_container_add(GTK_CONTAINER(btn_align), exit_btn);
    gtk_box_pack_end(GTK_BOX(vbox), btn_align, FALSE, FALSE, 0);

    gtk_widget_show_all(window);
    gtk_main();

    return 0;
}
