# FAQ

## The container doesn't start!

Verify that the port is not already used (typically, by another container). You may do so by running `docker ps | grep PORTNUMBER`

## How do I setup user accounts?

The standalone registry does not provide account management. For simple
access control, you can set up an nginx or Apache frontend with basic
auth enabled (see the (advanced documentation)[ADVANCED.md] for more about that).


## How do I report a bug?

Please insert the following into your bug report:

 * your registry version
 * specify how you are using your registry (container or pip)
 * specify what storage backend you use
 * restart your registry with the `DEBUG=true` environment variable set, and copy the output of `curl https://myregistry/_ping`
 * possibly copy any stack trace that you have
 
Please, no "this happens to me as well" comments on tickets - not helpful.

On the other hand, if you do have any useful information to provide, by all means do. 
