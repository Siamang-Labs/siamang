# Sign Up and Sign In

This page covers getting into Siamang Studio: creating an account, confirming
your email, signing in with a password or with Google or Microsoft, resetting a
forgotten password, staying signed in, and joining an organization from an
invitation. It ends with a table of the messages you may see and what they
mean.

---

## The sign-in screen

Go to **`studio.siamang.org`**. If you are not signed in, you land on the
sign-in card. On a wide screen the card sits next to a short introduction to
the product.

```
┌────────────────────────────────────────────┐
│  Siamang Studio  Beta                  ☾   │
│                                            │
│  Sign in                                   │
│  Research-as-code platform for your team.  │
│                                            │
│  [ G  Continue with Google            ]    │
│  [ ⊞  Continue with Microsoft         ]    │
│                  or                        │
│  [    Continue with Email          →  ]    │
│                                            │
│  Secured by Supabase.                      │
│  Terms of Use · Privacy Policy             │
│  Developed by Siamang Labs.                │
└────────────────────────────────────────────┘
```

- The **Beta** label next to the wordmark tells you the product is in open beta.
- The moon/sun button in the corner (**Toggle theme**) switches the page
  between light and dark. It uses the same saved choice as the app. See
  [[Account and Profile|Studio-Account-and-Profile]].
- The sign-in screen may also show **Continue with GitHub** if it is enabled
  for your deployment.
- **Terms of Use** and **Privacy Policy** open the legal texts on `siamang.org`.

There is no separate "Sign up" button. **Continue with Email** asks for your
address first and then decides for you: sign in if the address has an account,
sign up if it does not.

---

## Every step of the sign-in card

| Step | Heading | What it says | Controls |
|---|---|---|---|
| Start | **Sign in** | "Research-as-code platform for your team." | **Continue with Google**, **Continue with Microsoft**, then **Continue with Email** |
| Email | **Continue with email** | "Enter your email to sign in or create an account." | **Email** (placeholder `you@agency.com`), **Continue** (shows "Checking…"), **← Back** |
| Password | **Welcome back** | "Enter your password for *your address*." | **Password** with **Show**/**Hide**, a captcha if configured, **Sign in** (shows "Signing in…"), **← Different email**, **Forgot password?** |
| Sign-up | **Create your account** | "No account for *your address* yet — let's set one up. You'll get your own workspace on a 30-day Pro trial." | the Google/Microsoft buttons again, **Name** (placeholder `Jane Doe`), **Password** with **Show**/**Hide** (placeholder "at least 8 characters"), the password checklist, a captcha if configured, **Create account** (shows "Creating…"), **← Use a different email** |
| Forgot | **Reset your password** | "Enter your email and we'll send you a link to reset your password." | **Email**, a captcha if configured, **Send reset link** (shows "Sending…"), **← Back to sign in** |
| Reset link sent | **Check your email** | "We sent a password reset link to *your address*. Click the link in the email to reset your password." / "Didn't receive it? Check your spam folder or try again." | **Try again**, **← Back to sign in** |
| New password | **Set new password** | "Enter your new password below." | **New password** with **Show**/**Hide** and the checklist, **Confirm new password** (placeholder "repeat your password"), **Update password** (shows "Updating…"), **← Back to sign in** |
| Done | **Password updated** | "Your password has been successfully reset. You can now sign in with your new password." | **Sign in** |
| Confirm email | **Confirm your email** | "We sent a confirmation link to *your address*. Please check your inbox and click the link to activate your account." / "After confirming, come back here and sign in." | **Back to sign in** |

If something goes wrong, a red line appears above the main button. The
messages are listed under [Troubleshooting](#troubleshooting).

On the **Continue with email** step, Studio moves on only when it knows the
answer: **Welcome back** if the address has an account, **Create your
account** if it definitely has none. If the lookup itself fails (your
connection dropped, Studio is busy, or too many people on your network are
signing in at once), the card stays on the email step with a line such as
"Could not check your email. Too many sign-in attempts from your network just
now — wait a minute and try again." Click **Continue** again when you are
ready. A failed lookup never sends you to the sign-up form.

---

## Create an account

1. Click **Continue with Email**.
2. Type your email address and click **Continue**.
3. Studio finds no account for that address and shows **Create your account**.
   Check the address shown in the sentence at the top. Studio will create an
   account for exactly what you typed, typos included.
4. Enter your **Name**. Colleagues see it next to your Saves, comments and
   activity.
5. Choose a **Password** that meets every rule in the checklist (below).
   **Show** reveals what you typed.
6. If a captcha box appears, complete it (usually none does).
7. Click **Create account**.

There is no "repeat password" field on this form. Use **Show** to check what
you typed before you submit.

### Password rules

The checklist under the password field (in two columns) checks each rule off
as you type (○ becomes ✓). **Create account** stays disabled until all five are met.

| Checklist item | Rule |
|---|---|
| **At least 8 characters** | length 8 or more |
| **A lowercase letter** | at least one of `a`–`z` |
| **An uppercase letter** | at least one of `A`–`Z` |
| **A number** | at least one digit `0`–`9` |
| **A symbol (e.g. ! ? @ #)** | at least one character that is not an unaccented letter or a digit. A space or an accented letter also counts. |

The same rules apply when you set a new password after a reset and when you
change it in your profile.

### The captcha

A Cloudflare Turnstile check runs on the sign-up, sign-in and reset forms.
Usually it passes on its own and nothing appears: the form's button enables a
moment after. A small box appears, in the middle of the card, only when
Cloudflare needs you to do something. The button stays disabled until the
check has passed. If an attempt fails (a wrong password, say), the check
resets for the next try. The check is loaded from Cloudflare when one of those
forms opens, not on the first, email step (see
[Cookies and browser storage](Studio-Security-and-Privacy#cookies-and-browser-storage)).

### Confirm your email

After **Create account** you normally see **Confirm your email**, and a
message arrives in your inbox.

1. Open the email and click the confirmation link.
2. The link brings you back to Studio and usually signs you straight in. If
   you land on the sign-in card instead, sign in with your email and password.

Until the address is confirmed, signing in with the password is refused.
Nothing arrived? Check your spam folder, and check the address on the
**Confirm your email** screen for typos.

---

## What you get when you sign up

Every new account gets its own workspace straight away. This happens whether
you signed up with email or with Google or Microsoft:

- **An organization named after you.** Its name is the name you entered, for
  example "Jane Doe", and you can rename it later. Its address (slug) is
  derived from that name with `-org` added, for example `jane-doe-org`, and
  cannot be changed.
- **You are its owner.**
- **It is a cooperative organization**, so you can invite colleagues right
  away. See [[Organizations and Team|Studio-Organizations-and-Team]].
- **A 30-day Pro trial** with no card required. The topbar shows a
  `Pro trial · 30d` pill that counts down. A few things stay locked during an
  unpaid trial: email invitations to respondents, and the AI assistant runs on
  a small one-off allowance. When the trial ends, the organization moves to the
  **Free** plan. Nothing is deleted and it does **not** become read-only. See
  [[Plans, Trial and Billing|Studio-Plans-and-Billing]].

One trial per email address. Addresses are matched without regard to
upper/lower case, and accounts are not deleted, so signing up again with the
same address does not give you a new trial. Organizations you add later with
**Create organization** start on the Free plan (see
[Creating another organization](Studio-Organizations-and-Team#creating-another-organization)).

After sign-in you arrive on the **Projects** tab of the organization you
joined first. For a new account that is this workspace, unless you created
the account with an address that had been invited to another organization:
then the inviting organization opens first (see
[If you create your account from the invitation](#if-you-create-your-account-from-the-invitation)).
The workspace chip in the topbar switches between your organizations.

---

## Sign in with email and password

1. Click **Continue with Email**, type your address and click **Continue**.
2. On **Welcome back**, enter your password and click **Sign in**.

**← Different email** takes you back to the address step.

## Sign in with Google or Microsoft

Click **Continue with Google** or **Continue with Microsoft** and complete the
provider's sign-in. You return to Studio signed in. The first time, your Studio
account and your trial workspace are created automatically, and any pending
invitations to your address are accepted with it. The same buttons
appear on the **Create your account** step, so you can switch to a provider
there too.

**Linking.** Accounts are matched by email address. If you signed up with a
password and later use Google with the same address, you get the same Studio
account, not a second one. The provider must confirm that the address is
verified. If it doesn't, Studio refuses the sign-in (see
[Troubleshooting](#troubleshooting)).

**Two-factor authentication.** Studio has no two-factor authentication of its
own in the beta. Signing in with Google or Microsoft uses whatever second
factor your provider requires. This is the recommended route for sensitive
studies.

---

## Forgotten password

1. Click **Continue with Email**, type your address, click **Continue**.
2. On **Welcome back**, click **Forgot password?**.
3. Check the address, solve the captcha if one appears, and click
   **Send reset link**.
4. You see **Check your email**. Open the message and click the link.
5. Studio opens **Set new password**. Type the new password, confirm it, and
   click **Update password**.
6. On **Password updated**, click **Sign in** and use the new password.

> **Tip.** Open the reset link while you are **signed out** of Studio, or in a
> private browser window. If you are signed in when you click it, Studio takes
> you into the app instead of showing the **Set new password** form.

If the link no longer works, go back to **Reset your password** and request a
new one (**Try again** on the **Check your email** screen does the same).

**Accounts created with Google or Microsoft** have no Studio password to begin
with. Keep using the provider button, or set a password as described in
[[Account and Profile|Studio-Account-and-Profile]].

---

## Staying signed in and signing out

- While you work, Studio renews your sign-in in the background, so an open tab
  does not suddenly log you out.
- If your sign-in cannot be renewed, you are returned to the sign-in card with
  the note "Your session expired. Please sign in again." This can happen after
  a long time offline, for example.
- If you don't open Studio for about a week, it asks you to sign in again.
- **Sign out** is at the bottom of the avatar menu (top right). It ends the
  session in this browser and invalidates its sign-in token.
- While you are signed in, the sign-in page is skipped: going to
  `studio.siamang.org` takes you straight to your workspace.

---

## Joining an organization from an invitation

An owner or admin of an organization invites you by email address (see
[Inviting people](Studio-Organizations-and-Team#inviting-people)). What happens
next depends on whether that address already has a Studio account.

### If you already have an account

You are **added to the organization immediately**. No email is sent and there
is nothing to accept. The next time you open or reload Studio, the
organization appears in the **workspace chip** menu in the topbar, with the
role you were given. Pick it there to switch.

### If you don't have an account yet

You receive an email:

- **Subject:** "*Inviter* invited you to *Organization* on Siamang Studio"
- **Body:** "*Inviter* invited you to join *Organization* as *role* on Siamang
  Studio.", then "Accept the invitation:" followed by the link, then "The link
  is valid for 7 days. If you didn't expect this email, ignore it."

The link opens an invitation page at `studio.siamang.org/invite/…`:

```
Siamang Studio

Maria Lopez invited you to join Acme Research as member.
Sent to j***@example.com. The link is valid until 10/7/2026.

Sign in (or create an account) with the invited email to accept.
[ Sign in to accept ]
```

- The address is shown masked (first letter only), so you can tell which
  mailbox the invitation is for.
- **Sign in to accept** takes you to the sign-in card. Create your account
  there with the invited address, as described below. You are brought back to
  the invitation page, and from there into the organization.
- If you come back signed in and the page shows **Accept invitation**, click
  it ("Joining…"). With the invited address you land in that organization's
  **Projects**; with another address the page tells you which one to use (see
  [Invitation page messages](#invitation-page-messages)).
- You must use the **same email address** the invitation was sent to. Upper
  and lower case don't matter.

### If you create your account from the invitation

When you create a new account with the invited address, whether on the
**Create your account** step or with Google or Microsoft, Studio adds you to
the inviting organization, with the role in the invitation, as your account is
set up. You don't need to click anything else. The invitation page you are
brought back to takes you straight into that organization, on its
**Projects** tab.

The inviting organization is also the one that opens first when you sign in
later. Studio opens the organization you joined first, and of the
organizations you joined when your account was set up, the inviting one is
older than your new trial workspace (with invitations from several
organizations, the oldest of them opens). Your own trial workspace is listed
in the **workspace chip** menu; pick it there to switch.

Good to know:

- Invitations are matched by address. An account set up with an invited
  address joins every organization that has a pending invitation for it, even
  if you never opened the link.
- If the inviting organization has no room left on its plan, that invitation
  stays pending. The invitation page then shows **Accept invitation**, and
  accepting answers "Could not accept the invitation. Plan 'free' allows up to
  2 members; upgrade to add more." Accept it again once the owner has upgraded
  or made room. If an owner or admin adds you directly in the meantime, the
  invitation is closed; opening the link while signed in takes you into the
  organization.
- Opening the link again later, signed in with the account that used it or
  after you were added directly, takes you into the organization instead of
  showing an error.

### Invitation page messages

| Message | What it means |
|---|---|
| **Loading invitation…** | the page is looking the invitation up |
| "This invitation has expired. Ask the person who invited you to send a new one." | more than 7 days have passed |
| "This invitation link is invalid or has already been used." | the invitation was already used, revoked by an admin or replaced by a newer invitation to the same address; an owner or admin already added you to the organization directly; or the link was copied incompletely. If your own account used it, or you were added directly, and you are signed out, sign in and open the link again: it takes you into the organization. |
| "Could not load the invitation. …" | the page could not look the invitation up just then. The rest of the line gives the reason, for example "The server could not be reached — check your connection and try again." or, after many reloads in a minute, "Rate limit exceeded; slow down." The link itself may be fine: click **Try again**. |
| "This invitation was sent to j***@example.com — sign in with that account to accept it." | you are signed in with a different address. Sign out and sign in with the invited one. |
| "Could not accept the invitation. Plan 'free' allows up to 2 members; upgrade to add more." | the organization is full on its plan. Ask its owner to upgrade, then accept again. |

Error states show a button: **Go to the console** if you are signed in, **Go
to sign in** if not. When the page could not load the invitation, a **Try
again** button comes first.

---

## Troubleshooting

| You see | Why, and what to do |
|---|---|
| **Create your account** although you already have an account | Studio shows this step only when it found no account for the address you typed, so check the address in the sentence at the top for a typo. Go **← Use a different email** and type it again. If you signed up but never clicked the confirmation link, find that email first. |
| "Could not check your email. Too many sign-in attempts from your network just now — wait a minute and try again." | From one network address, Studio answers at most 10 lookups a minute for the same email, and at most 20 a minute for all emails together. Repeated tries, or many people signing in at once from a shared network such as a classroom or an office, can reach that. Wait a minute and click **Continue** again. |
| "Could not check your email. The server could not be reached — check your connection and try again." | The lookup never reached Studio. Check your connection and click **Continue** again. Other reasons after "Could not check your email." (for example "The server is having trouble — try again in a moment." or "The server did not say whether this email has an account — try again.") mean the same: try again shortly. |
| "This email already has an account — sign in instead." | You tried to sign up with an address that already has an account. Use **← Use a different email**, then sign in. |
| "Could not sign you in. Invalid login credentials." | Wrong password, or the account was created with Google or Microsoft and has no password. Use **Forgot password?** or the provider button. |
| "Could not sign you in. Email not confirmed." | Click the link in the confirmation email first. |
| "Sign in failed. This e-mail address is not verified by the identity provider; verify it there, then sign in again." | Your Google or Microsoft account reports the email address as unverified. Verify it with the provider, then try again. |
| "Your session expired. Please sign in again." | Your sign-in could not be renewed. Sign in again; no work is lost. Unsaved edits are kept as drafts. |
| The reset or confirmation link opened the app instead of a form | You were already signed in. Sign out (or use a private window) and click the link again. |
| "Passwords do not match." | The two fields on **Set new password** differ. |
| "Password must be 8+ characters with a lower- and upper-case letter, a number, and a symbol." | The new password misses a rule from the checklist. |
| "Could not send recovery email. …" | The reset email could not be requested. The second sentence gives the reason (for example, a new link requested too soon after the last one). Wait a little and try again. |
| "Could not create your account. …" / "Could not reset your password. …" / "Could not sign you in with that provider. …" | The action failed. The sentence after the first gives the reason. |
| The **Sign in** or **Create account** button stays gray | Solve the captcha, and for sign-up fill in the name and meet every password rule. |
| Nothing arrives by email | Check spam and the address you typed. Reset emails can be requested again from **Reset your password**. |

Still stuck? Write to `info@siamang-team.org` from the address you use for
Studio.

## See also

- [[Account and Profile|Studio-Account-and-Profile]]
- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[Plans, Trial and Billing|Studio-Plans-and-Billing]]
- [[Security and Privacy|Studio-Security-and-Privacy]]
- [[Quick Start|Studio-Quick-Start]]

<!-- studio-nav -->
---

← [[Tutorial: A Study from Start to Finish|Studio-Tutorial-End-to-End]] · [Studio contents](Studio-Overview#all-pages) · [[Account and Profile|Studio-Account-and-Profile]] →
