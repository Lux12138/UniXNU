/* Darwin's copyfile(3) for building xnu's SETUP/installfile on Linux. */
#define _GNU_SOURCE
#include <copyfile.h>

#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

const char *copyfile_strerror(int error)
{
	return strerror(error);
}

int fcopyfile(int from_fd, int to_fd, copyfile_state_t state, uint32_t flags)
{
	(void)state;
	(void)flags;

	if (from_fd < 0 || to_fd < 0) {
		errno = EBADF;
		return -1;
	}

	char buffer[65536];
	ssize_t got;
	int result = 0;

	while ((got = read(from_fd, buffer, sizeof(buffer))) > 0) {
		ssize_t written = 0;
		while (written < got) {
			ssize_t n = write(to_fd, buffer + written, (size_t)(got - written));
			if (n < 0) {
				return -1;
			}
			written += n;
		}
	}
	if (got < 0) {
		result = -1;
	}
	return result;
}

int copyfile(const char *from, const char *to, copyfile_state_t state, uint32_t flags)
{
	(void)state;

	if (from == NULL || to == NULL) {
		errno = EINVAL;
		return -1;
	}

	/* Only the data copy has meaning on Linux; the metadata flags are accepted and ignored so a
	 * caller passing COPYFILE_ALL behaves like the Darwin original for file contents. */
	(void)flags;

	int in = open(from, O_RDONLY);
	if (in < 0) {
		return -1;
	}

	int out = open(to, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	if (out < 0) {
		int saved = errno;
		close(in);
		errno = saved;
		return -1;
	}

	char buffer[65536];
	ssize_t got;
	int result = 0;

	while ((got = read(in, buffer, sizeof(buffer))) > 0) {
		ssize_t written = 0;
		while (written < got) {
			ssize_t n = write(out, buffer + written, (size_t)(got - written));
			if (n < 0) {
				result = -1;
				goto done;
			}
			written += n;
		}
	}
	if (got < 0) {
		result = -1;
	}

done:
	{
		int saved = errno;
		close(in);
		if (close(out) < 0 && result == 0) {
			result = -1;
		}
		errno = saved;
	}
	return result;
}
