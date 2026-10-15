import { Link } from '@tanstack/react-router';
import { useDocumentTitle } from '@/hooks/use-document-title';
import { Logo } from '@/components/patterns/logo';
import { ThemeToggle } from '@/components/patterns/theme-toggle';
import { Button } from '@/components/ui/button';
import { SlackMark } from '@/components/patterns/slack-mark';
import { UsersThree, ListChecks } from '@/icons';
import { LockedRowFigure } from './locked-row-figure';
import { PermissionFigure } from './permission-figure';
import { RevisionTable } from './revision-table';
import { Sheet } from './sheet';
import { SignupStart } from './signup-start';
import { SlackFlowFigure } from './slack-flow-figure';
import { SlackMappingFigure } from './slack-mapping-figure';
import { TasksNotesFigure } from './tasks-notes-figure';
import { TitleBlock } from './title-block';

function Header() {
	return (
		<header className='flex h-12 items-center gap-4 border-b bp-rule-strong px-4'>
			<Link to='/' aria-label='Pro-Goal home' className='tap-target'>
				<Logo />
			</Link>
			<nav
				aria-label='Page'
				className='ml-4 hidden items-center gap-1 text-sm sm:flex'
			>
				<Button
					variant='ghost'
					size='sm'
					nativeButton={false}
					render={<a href='#collaboration' />}
				>
					Collaboration
				</Button>
				<Button
					variant='ghost'
					size='sm'
					nativeButton={false}
					render={<a href='#tasks' />}
				>
					Tasks and notes
				</Button>
				<Button
					variant='ghost'
					size='sm'
					nativeButton={false}
					render={<a href='#slack' />}
				>
					Slack
				</Button>
				<Button
					variant='ghost'
					size='sm'
					nativeButton={false}
					render={<a href='#permissions' />}
				>
					Permissions
				</Button>
			</nav>
			<div className='ml-auto flex items-center gap-2'>
				<ThemeToggle />
				<Button
					variant='outline'
					size='sm'
					nativeButton={false}
					render={<Link to='/login' />}
				>
					Sign in
				</Button>
			</div>
		</header>
	);
}

function Footer() {
	return (
		<footer className='border-t bp-rule-strong px-4 py-4 text-sm'>
			<div className='flex flex-wrap items-center gap-x-6 gap-y-2'>
				<Logo mark />
				<Link
					to='/login'
					className='tap-target bp-muted underline-offset-4 hover:underline'
				>
					Sign in
				</Link>
				<Link
					to='/signup'
					className='tap-target bp-muted underline-offset-4 hover:underline'
				>
					Create account
				</Link>
				<Link
					to='/terms'
					className='tap-target bp-muted underline-offset-4 hover:underline sm:ml-auto'
				>
					Terms
				</Link>
				<Link
					to='/privacy'
					className='tap-target bp-muted underline-offset-4 hover:underline'
				>
					Privacy
				</Link>
			</div>
		</footer>
	);
}

export function LandingPage() {
	useDocumentTitle(
		'Pro-Goal · Projects, tasks and notes in one app and Slack',
	);
	return (
		<Sheet sheet='PG-01' rev='C'>
			<div className='flex flex-1 flex-col'>
				<Header />
				<main
					id='main'
					tabIndex={-1}
					className='flex-1 focus:outline-none'
				>
					<section className='grid gap-x-10 gap-y-6 px-4 py-8 lg:grid-cols-[1fr_22rem] lg:grid-rows-[auto_1fr] lg:py-6'>
						<div className='min-w-0 lg:col-start-1 lg:row-start-1'>
							<h1 className='max-w-[20ch] text-4xl font-semibold tracking-tight sm:text-5xl lg:text-4xl lg:leading-[1.1] xl:text-5xl'>
								Projects, tasks and notes, all in one app with
								Slack.
							</h1>
							<p className='mt-3 max-w-xl text-base bp-muted sm:mt-4 sm:text-lg lg:text-base'>
								Pro-Goal is a project tracker where each project
								is its own space. Your team shares tasks,
								subtasks, notes and comments, and Slack gets the
								updates. Look around shared demo projects first,
								then start your own.
							</p>
							<ul className='mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm font-medium'>
								<li className='inline-flex items-center gap-2'>
									<UsersThree
										className='size-5'
										aria-hidden
									/>
									Project collaboration
								</li>
								<li className='inline-flex items-center gap-2'>
									<ListChecks
										className='size-5'
										aria-hidden
									/>
									Tasks and notes
								</li>
								<li className='inline-flex items-center gap-2'>
									<SlackMark className='size-6' />
									Slack integration
								</li>
							</ul>
						</div>
						<div className='lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:pt-2'>
							<TitleBlock
								title='Start a project'
								subtitle='Create your account in a minute. Free to start.'
							>
								<SignupStart />
							</TitleBlock>
							<p className='mt-3 text-sm bp-muted'>
								Already have an account?{' '}
								<Link
									to='/login'
									className='font-medium text-primary underline-offset-4 hover:underline'
								>
									Sign in
								</Link>
							</p>
						</div>
						<div className='min-w-0 lg:col-start-1 lg:row-start-2'>
							<SlackFlowFigure />
						</div>
					</section>

					<section
						id='collaboration'
						className='scroll-mt-16 border-t bp-rule-strong px-4 py-12'
					>
						<div className='grid gap-8 lg:grid-cols-[18rem_1fr]'>
							<div>
								<h2 className='text-2xl font-semibold tracking-tight'>
									Your team joins with a code.
								</h2>
								<p className='mt-3 bp-muted'>
									Share a 6-character code or list your
									project on Explore. You review each request,
									pick a role, and the person is in.
									Everything is undoable.
								</p>
							</div>
							<div>
								<RevisionTable />
							</div>
						</div>
					</section>

					<section
						id='tasks'
						className='scroll-mt-16 border-t bp-rule-strong px-4 py-12'
					>
						<div className='grid gap-8 lg:grid-cols-[18rem_1fr]'>
							<div>
								<h2 className='text-2xl font-semibold tracking-tight'>
									Tasks and notes, side by side.
								</h2>
								<p className='mt-3 bp-muted'>
									Break work into tasks and subtasks, sort the
									board by status or priority, and keep notes
									and comments on the same page as the work.
								</p>
							</div>
							<div>
								<TasksNotesFigure />
							</div>
						</div>
					</section>

					<section
						id='slack'
						className='scroll-mt-16 border-t bp-rule-strong px-4 py-12'
					>
						<div className='grid gap-8 lg:grid-cols-[18rem_1fr]'>
							<div>
								<h2 className='flex items-center gap-2 text-2xl font-semibold tracking-tight'>
									<SlackMark className='size-7 shrink-0' />
									Your team hears about it in Slack.
								</h2>
								<p className='mt-3 bp-muted'>
									Connect a Slack workspace, point each
									project at a channel, and pick which events
									post: new tasks, assignments, comments, join
									requests. Every delivery is logged.
								</p>
							</div>
							<div>
								<SlackMappingFigure />
							</div>
						</div>
					</section>

					<section
						id='permissions'
						className='scroll-mt-16 border-t bp-rule-strong px-4 py-12'
					>
						<div className='grid gap-8 lg:grid-cols-[18rem_1fr]'>
							<div>
								<h2 className='text-2xl font-semibold tracking-tight'>
									You decide who can change what.
								</h2>
								<p className='mt-3 bp-muted'>
									Everyone can read everything. You grant
									changes field by field, and a locked field
									tells people why and who to ask.
								</p>
							</div>
							<div className='space-y-10'>
								<PermissionFigure />
								<LockedRowFigure />
							</div>
						</div>
					</section>

					<section className='border-t bp-rule-strong px-4 pt-12 pb-20'>
						<div className='grid items-start gap-8 lg:grid-cols-[1fr_22rem]'>
							<div>
								<h2 className='text-3xl font-semibold tracking-tight'>
									Start a project in a minute.
								</h2>
								<p className='mt-3 max-w-lg bp-muted'>
									Create an account, explore the demos, make a
									project, and connect Slack when you are
									ready.
								</p>
							</div>
							<div>
								<TitleBlock title='Start a project'>
									<SignupStart />
								</TitleBlock>
							</div>
						</div>
					</section>
				</main>
				<Footer />
			</div>
		</Sheet>
	);
}
