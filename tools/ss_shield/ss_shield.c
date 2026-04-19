/*
 * ss_shield - Full-screen override-redirect X11 window for Kindle
 *
 * Creates an invisible shield window on top of all other windows,
 * preventing the status bar (clock, wifi, battery) from painting
 * over FBInk's framebuffer content during screensaver mode.
 *
 * Override-redirect windows bypass the window manager and are
 * composited on top of all managed windows by the X server itself.
 *
 * Usage: DISPLAY=:0 ss_shield &
 *        kill $! to remove the shield
 */

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/select.h>
#include <unistd.h>

static int signal_pipe[2];

static void on_signal(int sig) {
    (void)sig;
    char c = 'x';
    write(signal_pipe[1], &c, 1);
}

int main(void) {
    Display *dpy;
    Window win;
    XSetWindowAttributes attrs;
    int screen;
    XEvent ev;

    fprintf(stderr, "ss_shield: starting\n");

    if (pipe(signal_pipe) < 0) {
        fprintf(stderr, "ss_shield: pipe() failed\n");
        return 1;
    }

    dpy = XOpenDisplay(NULL);
    if (!dpy) {
        fprintf(stderr, "ss_shield: cannot open display (DISPLAY=%s)\n",
                getenv("DISPLAY") ? getenv("DISPLAY") : "(unset)");
        return 1;
    }

    screen = DefaultScreen(dpy);
    int width = DisplayWidth(dpy, screen);
    int height = DisplayHeight(dpy, screen);
    fprintf(stderr, "ss_shield: display opened, screen %d, size %dx%d\n",
            screen, width, height);

    attrs.override_redirect = True;
    attrs.background_pixel = BlackPixel(dpy, screen);
    attrs.event_mask = VisibilityChangeMask | ExposureMask;

    win = XCreateWindow(
        dpy, RootWindow(dpy, screen),
        0, 0, width, height,
        0,
        CopyFromParent, InputOutput, CopyFromParent,
        CWOverrideRedirect | CWBackPixel | CWEventMask,
        &attrs
    );
    fprintf(stderr, "ss_shield: window created (id=0x%lx, %dx%d, override_redirect=True)\n",
            win, width, height);

    XMapRaised(dpy, win);
    XFlush(dpy);
    fprintf(stderr, "ss_shield: window mapped and raised\n");

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);

    int x11_fd = ConnectionNumber(dpy);
    int max_fd = (x11_fd > signal_pipe[0]) ? x11_fd : signal_pipe[0];
    fd_set fds;

    fprintf(stderr, "ss_shield: running (PID %d), waiting for events\n", getpid());

    for (;;) {
        FD_ZERO(&fds);
        FD_SET(x11_fd, &fds);
        FD_SET(signal_pipe[0], &fds);

        if (select(max_fd + 1, &fds, NULL, NULL, NULL) < 0)
            break;

        if (FD_ISSET(signal_pipe[0], &fds))
            break;

        while (XPending(dpy)) {
            XNextEvent(dpy, &ev);
            if (ev.type == VisibilityNotify) {
                const char *state;
                switch (ev.xvisibility.state) {
                    case VisibilityUnobscured: state = "Unobscured"; break;
                    case VisibilityPartiallyObscured: state = "PartiallyObscured"; break;
                    case VisibilityFullyObscured: state = "FullyObscured"; break;
                    default: state = "Unknown"; break;
                }
                fprintf(stderr, "ss_shield: visibility changed = %s\n", state);
            }
        }
    }

    fprintf(stderr, "ss_shield: shutting down\n");
    XDestroyWindow(dpy, win);
    XCloseDisplay(dpy);
    close(signal_pipe[0]);
    close(signal_pipe[1]);
    return 0;
}
