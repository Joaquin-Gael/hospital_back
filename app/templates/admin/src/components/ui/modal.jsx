import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Cross2Icon } from '@radix-ui/react-icons';
import { clsx } from 'clsx';

const Modal = React.forwardRef(({ children, className, ...props }, ref) => (
  <Dialog.Root {...props}>
    {children}
  </Dialog.Root>
));
Modal.displayName = 'Modal';

const ModalTrigger = React.forwardRef(({ className, ...props }, ref) => (
  <Dialog.Trigger
    ref={ref}
    className={clsx(
      'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      'disabled:pointer-events-none disabled:opacity-50',
      'bg-primary text-primary-foreground hover:bg-primary/90',
      'h-10 px-4 py-2',
      className
    )}
    {...props}
  />
));
ModalTrigger.displayName = 'ModalTrigger';

const ModalContent = React.forwardRef(({ className, children, ...props }, ref) => (
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm" />
    <Dialog.Content
      ref={ref}
      className={clsx(
        'fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-card p-6 shadow-lg duration-200',
        'border-border rounded-[var(--radius)]',
        'animate-in fade-in-0 zoom-in-95 slide-in-from-left-1/2 slide-in-from-top-[48%]',
        className
      )}
      {...props}
    >
      {children}
      <Dialog.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none">
        <Cross2Icon className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
));
ModalContent.displayName = 'ModalContent';

const ModalHeader = ({ className, ...props }) => (
  <div
    className={clsx('flex flex-col space-y-1.5 text-center sm:text-left', className)}
    {...props}
  />
);
ModalHeader.displayName = 'ModalHeader';

const ModalFooter = ({ className, ...props }) => (
  <div
    className={clsx('flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2', className)}
    {...props}
  />
);
ModalFooter.displayName = 'ModalFooter';

const ModalTitle = React.forwardRef(({ className, ...props }, ref) => (
  <Dialog.Title
    ref={ref}
    className={clsx('text-lg font-semibold leading-none tracking-tight', className)}
    {...props}
  />
));
ModalTitle.displayName = 'ModalTitle';

const ModalDescription = React.forwardRef(({ className, ...props }, ref) => (
  <Dialog.Description
    ref={ref}
    className={clsx('text-sm text-muted-foreground', className)}
    {...props}
  />
));
ModalDescription.displayName = 'ModalDescription';

export {
  Modal,
  ModalTrigger,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalTitle,
  ModalDescription,
};