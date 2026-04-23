bundle MyBundle {
    x = true
    y = [1, 2, 3]

    for item in y {
        z = item
    }

    File '/tmp/nginx.conf' {
        template: 'nginx.conf.j2',
        owner: 'king',
        mode: '0644',
    }
}
