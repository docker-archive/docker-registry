# -*- coding: utf-8 -*-

import logging
import logging.handlers


def _adapt_smtp_secure(value):
    """Adapt the value to arguments of ``SMTP.starttls()``

    .. seealso:: <http://docs.python.org/2/library/smtplib.html\
#smtplib.SMTP.starttls>

    """
    if isinstance(value, dict):
        logging.warning('Key/cert support is deprecated. If you use it\
            open a ticket on https://github.com/docker/docker-registry')
        assert set(value.keys()) == set(['keyfile', 'certfile'])
        return (value.keyfile, value.certfile)
    if value:
        return ()


def setup(level, mail):
    if level:
        level = level.upper()
    if not level or not hasattr(logging, level):
        level = 'INFO'
    level = getattr(logging, level)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(
        logging.Formatter(
            fmt='%(asctime)s %(levelname)s: %(message)s',
            datefmt="%d/%b/%Y:%H:%M:%S %z"))

    logger = logging.getLogger()
    logger.addHandler(stderr_handler)
    logger.setLevel(level)

    if mail and mail.smtp_host:
        mailhost = mail.smtp_host
        mailport = mail.smtp_port
        secure_args = _adapt_smtp_secure(mail.smtp_secure)
        if isinstance(mail.to_addr, basestring):
            mail.to_addr = [mail.to_addr]
        mail_handler = logging.handlers.SMTPHandler(
            mailhost=(mailhost, mailport) if mailport else mailhost,
            fromaddr=mail.from_addr,
            toaddrs=mail.to_addr,
            subject=mail.subject,
            credentials=(mail.smtp_login,
                         mail.smtp_password),
            secure=secure_args)
        mail_handler.setLevel(logging.ERROR)
        logging.getLogger().addHandler(mail_handler)
